from typing import Protocol

from ..errors import InvalidAnalysisRequestError


class BuildPromptInput(Protocol):
    content: str
    question: str | None
    mode: object


class BuildPromptUseCase:
    def execute(self, analysis_input: BuildPromptInput) -> str:
        if self._mode_value(analysis_input.mode) == "doc":
            return analysis_input.content

        if not analysis_input.question:
            raise InvalidAnalysisRequestError("la question est obligatoire en mode 'question'")

        return f"document :\\n{analysis_input.content}\\n\\nquestion : {analysis_input.question}"

    @staticmethod
    def _mode_value(mode: object) -> str:
        return str(getattr(mode, "value", mode))
