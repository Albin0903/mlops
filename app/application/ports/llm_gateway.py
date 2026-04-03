from typing import Any, AsyncGenerator, Protocol

from app.domain.provider import ProviderSelection


class LLMGateway(Protocol):
    def get_system_prompt(self, mode: str, language: str) -> str: ...

    def stream_response(
        self,
        prompt: str,
        system_message: str,
        mode: str,
        provider_selection: ProviderSelection,
        thinking: str | bool | None = None,
        json_format: bool = False,
    ) -> AsyncGenerator[str, None]: ...

    async def execute_agent_call(
        self,
        *,
        prompt: str,
        system_message: str,
        messages: list[dict[str, Any]] | None,
        tools: list[dict[str, object]] | None,
        provider_selection: ProviderSelection,
        thinking: str | bool | None,
    ) -> dict[str, object]: ...
