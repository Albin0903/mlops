import time
from typing import Any, AsyncGenerator

from loguru import logger

from app.core.config import settings
from app.services.llm.factory import get_provider

# Configuration des modeles par provider (version free tier)
PROVIDER_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-3.1-flash-lite-preview",
    "ollama": "qwen3.5:9b",  # Modele local par defaut
    "ollama-small": "qwen3.5:2b",  # Modele local leger
    "ollama-mini": "qwen3.5:0.8b",  # Modele local tres leger
    "instant": "llama-3.1-8b-instant",
    "medium": "llama-3.3-70b-versatile",
    "gpt": "openai/gpt-oss-120b",
}

# Prompts systeme optimises
SYSTEM_PROMPTS = {
    "doc": (
        "tu es un generateur de documentation technique. "
        "regle stricte : repond uniquement en markdown. "
        "pas d'introduction, pas de conclusion. "
        "structure : signature, description (1 ligne), parametres, retour, exemple. "
        "langue du code source : {language}."
    ),
    "question": (
        "tu es un assistant intelligent et logique. "
        "base ta reponse sur le document fourni. "
        "tu peux raisonner, deduire et faire des inferences logiques a partir du contexte. "
        "si le document ne contient aucune information pertinente, repond 'information non disponible dans le document'. "
        "reponse concise et argumentee. "
        "n'expose jamais ton raisonnement interne ni de chaine de pensee. "
        "langue du document : {language}."
    ),
}

PROMETHEUS_METRICS = {}


def _get_prometheus_metric(metric_name: str, factory):
    if metric_name not in PROMETHEUS_METRICS:
        PROMETHEUS_METRICS[metric_name] = factory()
    return PROMETHEUS_METRICS[metric_name]


class LLMService:
    """Service unifie pour l'acces aux LLMs (Groq, Gemini, Ollama)"""

    def get_system_prompt(self, mode: str, language: str) -> str:
        return SYSTEM_PROMPTS[mode].format(language=language)

    async def get_streaming_response(
        self,
        prompt: str,
        system_message: str,
        mode: str = "doc",
        provider: str = "groq",
        thinking: str | bool | None = None,
    ) -> AsyncGenerator[str, None]:
        """Genere une reponse en streaming avec observabilite et multi-provider"""

        # Determination du modele et du provider reel
        model = PROVIDER_MODELS.get(provider, provider)

        # Mapping des alias vers les implementations reelles
        if "gemini" in provider or "gemini" in model:
            real_provider_name = "gemini"
        elif "ollama" in provider or model.startswith("qwen"):
            real_provider_name = "ollama"
        else:
            real_provider_name = "groq"

        provider_impl = get_provider(real_provider_name)
        if not provider_impl:
            yield f"erreur : le provider {real_provider_name} n'est pas configure ou supporte."
            return

        start_time = time.perf_counter()
        full_response = []
        input_tokens = 0
        output_tokens = 0

        # Langfuse Tracing
        langfuse_generation = None
        if settings.langfuse_enabled:
            try:
                from langfuse import get_client

                langfuse: Any = get_client()
                langfuse_generation = langfuse.generation(
                    name=f"llm-{mode}-{real_provider_name}",
                    model=model,
                    input={"prompt": prompt, "system_message": system_message},
                    metadata={"provider": real_provider_name, "mode": mode, "model": model},
                )
            except Exception as e:
                logger.warning(f"langfuse init failed : {e}")

        try:
            async for content, in_tok, out_tok in provider_impl.stream_response(
                prompt, system_message, model, thinking=thinking
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
            if langfuse_generation:
                langfuse_generation.update(level="ERROR", status_message=str(e))
            return

        # Metriques et Logs
        latency = time.perf_counter() - start_time
        logger.info(f"llm call completed | provider={real_provider_name} | model={model} | latency={latency:.2f}s")

        self._record_metrics(real_provider_name, model, mode, input_tokens, output_tokens, latency)

        if langfuse_generation:
            try:
                langfuse_generation.end(
                    output="".join(full_response),
                    usage={"input": input_tokens, "output": output_tokens},
                    metadata={"latency_seconds": round(latency, 3)},
                )
            except Exception as e:
                logger.warning(f"langfuse logging end failed : {e}")

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
    ) -> dict[str, Any]:
        """Execute un appel agent non-streaming avec support des outils"""
        model = PROVIDER_MODELS.get(provider, provider)
        if "gemini" in provider or "gemini" in model:
            real_provider_name = "gemini"
        elif "ollama" in provider or model.startswith("qwen"):
            real_provider_name = "ollama"
        else:
            real_provider_name = "groq"

        if messages is None:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ]

        provider_impl = get_provider(real_provider_name)
        if not provider_impl:
            raise ValueError(f"Provider {real_provider_name} not configured.")

        return await provider_impl.execute_agent_call(messages, model, tools or [], thinking=thinking)

    def _record_metrics(self, provider, model, mode, in_tok, out_tok, latency):
        try:
            from prometheus_client import Counter, Histogram

            llm_requests_total = _get_prometheus_metric(
                "llm_requests_total",
                lambda: Counter("llm_requests_total", "total requests", ["provider", "model", "mode"]),
            )
            llm_tokens_total = _get_prometheus_metric(
                "llm_tokens_total",
                lambda: Counter("llm_tokens_total", "total tokens", ["provider", "model", "type"]),
            )
            llm_latency_seconds = _get_prometheus_metric(
                "llm_latency_seconds",
                lambda: Histogram("llm_latency_seconds", "latency", ["provider", "model"]),
            )

            llm_requests_total.labels(provider=provider, model=model, mode=mode).inc()
            llm_tokens_total.labels(provider=provider, model=model, type="input").inc(in_tok)
            llm_tokens_total.labels(provider=provider, model=model, type="output").inc(out_tok)
            llm_latency_seconds.labels(provider=provider, model=model).observe(latency)
        except Exception:
            pass


llm_service = LLMService()
