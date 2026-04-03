from app.application.ports.llm_gateway import LLMGateway
from app.application.use_cases.resolve_provider import ResolveProviderUseCase


class GenerateFullResponseUseCase:
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
        prompt: str,
        system_message: str,
        mode: str = "question",
        provider: str = "gemma4b",
        thinking: str | bool | None = None,
        json_format: bool = False,
    ) -> str:
        provider_selection = self._resolve_provider_use_case.execute(provider)
        chunks: list[str] = []

        async for chunk in self._llm_gateway.stream_response(
            prompt=prompt,
            system_message=system_message,
            mode=mode,
            provider_selection=provider_selection,
            thinking=thinking,
            json_format=json_format,
        ):
            chunks.append(chunk)

        return "".join(chunks)
