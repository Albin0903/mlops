from typing import Any

from loguru import logger

from app.application.ports.observability_gateway import ObservabilityGateway
from app.domain.usage import TokenUsage
from app.services.observability import LLMObservability


class DefaultObservabilityGateway(ObservabilityGateway):
    """Adapter bridge between application observability port and concrete observability service."""

    def __init__(self, observability: LLMObservability | None = None):
        self._observability = observability or LLMObservability()

    def start_generation(
        self,
        *,
        enabled: bool,
        mode: str,
        provider: str,
        model: str,
        prompt: str,
        system_message: str,
    ) -> Any | None:
        return self._observability.start_generation(
            enabled=enabled,
            mode=mode,
            provider=provider,
            model=model,
            prompt=prompt,
            system_message=system_message,
        )

    def mark_generation_error(self, generation: Any | None, error_message: str) -> None:
        self._observability.mark_generation_error(generation, RuntimeError(error_message))

    def end_generation(
        self,
        *,
        generation: Any | None,
        output: str,
        usage: TokenUsage,
        latency_seconds: float,
    ) -> None:
        self._observability.end_generation(
            generation,
            output,
            usage.input_tokens,
            usage.output_tokens,
            latency_seconds,
        )

    def record_success(
        self,
        *,
        provider: str,
        model: str,
        mode: str,
        usage: TokenUsage,
        latency_seconds: float,
    ) -> None:
        self._observability.record_metrics(
            provider=provider,
            model=model,
            mode=mode,
            in_tok=usage.input_tokens,
            out_tok=usage.output_tokens,
            latency=latency_seconds,
        )

    def record_error(
        self,
        *,
        provider: str,
        model: str,
        mode: str,
        error_message: str,
    ) -> None:
        logger.error(
            "llm error | provider={} | model={} | mode={} | error={}",
            provider,
            model,
            mode,
            error_message,
        )
