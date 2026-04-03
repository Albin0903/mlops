from typing import AsyncGenerator, Protocol

from app.domain.prompt import PromptSpec

from ..ports.llm_gateway import LLMGateway
from .build_prompt import BuildPromptUseCase
from .resolve_provider import ResolveProviderUseCase


class AnalysisInputData(Protocol):
    content: str
    language: str
    provider: str
    question: str | None
    mode: object


class AnalyzeStreamUseCase:
    def __init__(
        self,
        llm_gateway: LLMGateway,
        build_prompt_use_case: BuildPromptUseCase,
        resolve_provider_use_case: ResolveProviderUseCase,
    ):
        self._llm_gateway = llm_gateway
        self._build_prompt_use_case = build_prompt_use_case
        self._resolve_provider_use_case = resolve_provider_use_case

    def execute(self, analysis_input: AnalysisInputData) -> AsyncGenerator[str, None]:
        mode = self._mode_value(analysis_input.mode)
        prompt = self._build_prompt_use_case.execute(analysis_input)
        provider_selection = self._resolve_provider_use_case.execute(analysis_input.provider)
        system_message = self._llm_gateway.get_system_prompt(
            mode=mode,
            language=analysis_input.language,
        )

        prompt_spec = PromptSpec(
            mode=mode,
            language=analysis_input.language,
            system_message=system_message,
            user_prompt=prompt,
        )

        return self._llm_gateway.stream_response(
            prompt=prompt_spec.user_prompt,
            system_message=prompt_spec.system_message,
            mode=prompt_spec.mode,
            provider_selection=provider_selection,
            thinking=None,
            json_format=False,
        )

    @staticmethod
    def _mode_value(mode: object) -> str:
        return str(getattr(mode, "value", mode))
