import time
from typing import Any, AsyncGenerator, Callable

from loguru import logger

from app.application.ports.observability_gateway import ObservabilityGateway
from app.core.config import settings
from app.domain.usage import TokenUsage
from app.services import prompt_manager
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import get_provider
from app.services.provider_registry import PROVIDER_MODELS, resolve_provider_name

SYSTEM_PROMPTS = prompt_manager.SYSTEM_PROMPTS
ProviderGetter = Callable[[str], BaseLLMProvider | None]


class LLMService:
    """Service unifie pour l'acces aux LLMs (Groq, Gemini, Ollama)"""

    def __init__(
        self,
        observability_gateway: ObservabilityGateway | None = None,
        provider_getter: ProviderGetter | None = None,
    ):
        self._observability_gateway = observability_gateway
        self._provider_getter = provider_getter

    @staticmethod
    def _resolve_provider(provider: str, model: str) -> str:
        return resolve_provider_name(provider, model)

    def get_system_prompt(self, mode: str, language: str) -> str:
        return prompt_manager.build_system_prompt(mode, language)

    def _get_observability_gateway(self) -> ObservabilityGateway:
        # Supporte les instances construites via __new__ dans les tests.
        observability_gateway = getattr(self, "_observability_gateway", None)
        if observability_gateway is None:
            from app.infrastructure.adapters.observability_gateway import DefaultObservabilityGateway

            observability_gateway = DefaultObservabilityGateway()
            self._observability_gateway = observability_gateway
        return observability_gateway

    def _get_provider_getter(self) -> ProviderGetter:
        provider_getter = getattr(self, "_provider_getter", None)
        if provider_getter is None:
            provider_getter = get_provider
            self._provider_getter = provider_getter
        return provider_getter

    async def get_streaming_response(
        self,
        prompt: str,
        system_message: str,
        mode: str = "doc",
        provider: str = "groq",
        thinking: str | bool | None = None,
        json_format: bool = False,
        resolved_provider: str | None = None,
        resolved_model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Genere une reponse en streaming avec observabilite et multi-provider"""

        model = resolved_model or PROVIDER_MODELS.get(provider, provider)
        real_provider_name = resolved_provider or self._resolve_provider(provider, model)

        provider_impl = self._get_provider_getter()(real_provider_name)
        if not provider_impl:
            yield f"erreur : le provider {real_provider_name} n'est pas configure ou supporte."
            return

        start_time = time.perf_counter()
        full_response = []
        input_tokens = 0
        output_tokens = 0
        observability = self._get_observability_gateway()

        langfuse_generation = observability.start_generation(
            enabled=settings.langfuse_enabled,
            mode=mode,
            provider=real_provider_name,
            model=model,
            prompt=prompt,
            system_message=system_message,
        )

        try:
            async for content, in_tok, out_tok in provider_impl.stream_response(
                prompt, system_message, model, thinking=thinking, json_format=json_format
            ):
                if not content:
                    continue
                full_response.append(content)
                input_tokens = in_tok or input_tokens
                output_tokens = out_tok or output_tokens
                yield content

        except Exception as e:
            logger.error(f"erreur critique service llm ({real_provider_name}) : {e}")
            error_msg = "\n\n[Erreur technique lors de la generation du contenu.]"
            yield error_msg
            observability.mark_generation_error(langfuse_generation, str(e))
            observability.record_error(
                provider=real_provider_name,
                model=model,
                mode=mode,
                error_message=str(e),
            )
            return

        # Metriques et Logs
        latency = time.perf_counter() - start_time
        logger.info(f"llm call completed | provider={real_provider_name} | model={model} | latency={latency:.2f}s")

        usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        observability.record_success(
            provider=real_provider_name,
            model=model,
            mode=mode,
            usage=usage,
            latency_seconds=latency,
        )
        observability.end_generation(
            generation=langfuse_generation,
            output="".join(full_response),
            usage=usage,
            latency_seconds=latency,
        )

    async def get_full_response(
        self,
        prompt: str,
        system_message: str,
        mode: str = "doc",
        provider: str = "groq",
        thinking: str | bool | None = None,
    ) -> str:
        chunks = []
        async for content in self.get_streaming_response(prompt, system_message, mode, provider, thinking=thinking):
            chunks.append(content)
        return "".join(chunks)

    async def execute_agent_call(
        self,
        prompt: str = "",
        system_message: str = "",
        messages: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        provider: str = "groq",
        thinking: str | bool | None = None,
        resolved_provider: str | None = None,
        resolved_model: str | None = None,
    ) -> dict[str, Any]:
        """Execute un appel agent non-streaming avec support des outils"""
        model = resolved_model or PROVIDER_MODELS.get(provider, provider)
        real_provider_name = resolved_provider or self._resolve_provider(provider, model)

        if messages is None:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ]

        provider_impl = self._get_provider_getter()(real_provider_name)
        if not provider_impl:
            raise ValueError(f"Provider {real_provider_name} not configured.")

        return await provider_impl.execute_agent_call(messages, model, tools or [], thinking=thinking)

    def _record_metrics(self, provider, model, mode, in_tok, out_tok, latency):
        usage = TokenUsage(input_tokens=in_tok, output_tokens=out_tok)
        self._get_observability_gateway().record_success(
            provider=provider,
            model=model,
            mode=mode,
            usage=usage,
            latency_seconds=latency,
        )
