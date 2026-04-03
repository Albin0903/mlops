from app.application.ports.llm_gateway import LLMGateway
from app.application.use_cases.resolve_provider import ResolveProviderUseCase


class ExecuteAgentCallUseCase:
    def __init__(
        self,
        llm_gateway: LLMGateway,
        resolve_provider_use_case: ResolveProviderUseCase,
    ):
        self._llm_gateway = llm_gateway
        self._resolve_provider_use_case = resolve_provider_use_case

    async def execute(
        self,
        *,
        prompt: str = "",
        system_message: str = "",
        messages: list[dict[str, str]] | None = None,
        tools: list[dict[str, object]] | None = None,
        provider: str = "gemma4b",
        thinking: str | bool | None = None,
    ) -> dict[str, object]:
        provider_selection = self._resolve_provider_use_case.execute(provider)
        return await self._llm_gateway.execute_agent_call(
            prompt=prompt,
            system_message=system_message,
            messages=messages,
            tools=tools,
            provider_selection=provider_selection,
            thinking=thinking,
        )
