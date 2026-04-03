from typing import Any, AsyncGenerator

from app.domain.provider import ProviderSelection
from app.services.llm_service import LLMService


class LLMServiceGateway:
    def __init__(self, llm_service: LLMService):
        self._llm_service = llm_service

    def get_system_prompt(self, mode: str, language: str) -> str:
        return self._llm_service.get_system_prompt(mode, language)

    def stream_response(
        self,
        prompt: str,
        system_message: str,
        mode: str,
        provider_selection: ProviderSelection,
        thinking: str | bool | None = None,
        json_format: bool = False,
    ) -> AsyncGenerator[str, None]:
        return self._llm_service.get_streaming_response(
            prompt=prompt,
            system_message=system_message,
            mode=mode,
            provider=provider_selection.alias,
            thinking=thinking,
            json_format=json_format,
            resolved_provider=provider_selection.provider,
            resolved_model=provider_selection.model,
        )

    async def execute_agent_call(
        self,
        *,
        prompt: str,
        system_message: str,
        messages: list[dict[str, Any]] | None,
        tools: list[dict[str, object]] | None,
        provider_selection: ProviderSelection,
        thinking: str | bool | None,
    ) -> dict[str, object]:
        return await self._llm_service.execute_agent_call(
            prompt=prompt,
            system_message=system_message,
            messages=messages,
            tools=tools,
            provider=provider_selection.alias,
            thinking=thinking,
            resolved_provider=provider_selection.provider,
            resolved_model=provider_selection.model,
        )
