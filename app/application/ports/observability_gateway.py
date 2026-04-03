from typing import Any, Protocol

from app.domain.usage import TokenUsage


class ObservabilityGateway(Protocol):
    def start_generation(
        self,
        *,
        enabled: bool,
        mode: str,
        provider: str,
        model: str,
        prompt: str,
        system_message: str,
    ) -> Any | None: ...

    def mark_generation_error(self, generation: Any | None, error_message: str) -> None: ...

    def end_generation(
        self,
        *,
        generation: Any | None,
        output: str,
        usage: TokenUsage,
        latency_seconds: float,
    ) -> None: ...

    def record_success(
        self,
        *,
        provider: str,
        model: str,
        mode: str,
        usage: TokenUsage,
        latency_seconds: float,
    ) -> None: ...

    def record_error(
        self,
        *,
        provider: str,
        model: str,
        mode: str,
        error_message: str,
    ) -> None: ...
