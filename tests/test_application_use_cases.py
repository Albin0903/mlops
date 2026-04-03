"""Tests unitaires de la couche application."""

from dataclasses import dataclass

import pytest

from app.application.errors import InvalidAnalysisRequestError
from app.application.use_cases.analyze_stream import AnalyzeStreamUseCase
from app.application.use_cases.build_prompt import BuildPromptUseCase
from app.application.use_cases.execute_agent_call import ExecuteAgentCallUseCase
from app.application.use_cases.generate_full_response import GenerateFullResponseUseCase
from app.application.use_cases.health_check import HealthCheckUseCase
from app.application.use_cases.resolve_provider import ResolveProviderUseCase
from app.domain.provider import ProviderSelection


@dataclass
class FakeAnalysisInput:
    content: str
    language: str
    provider: str
    mode: object
    question: str | None = None


class Mode:
    def __init__(self, value: str):
        self.value = value


class FakeLLMGateway:
    def __init__(self):
        self.calls: list[tuple] = []

    def get_system_prompt(self, mode: str, language: str) -> str:
        self.calls.append(("system", mode, language))
        return "system prompt"

    def stream_response(
        self,
        prompt: str,
        system_message: str,
        mode: str,
        provider_selection: ProviderSelection,
        thinking: str | bool | None = None,
        json_format: bool = False,
    ):
        self.calls.append(("stream", prompt, system_message, mode, provider_selection, thinking, json_format))

        async def _stream():
            yield "chunk-1"
            yield "chunk-2"

        return _stream()

    async def execute_agent_call(
        self,
        *,
        prompt: str,
        system_message: str,
        messages: list[dict[str, str]] | None,
        tools: list[dict[str, object]] | None,
        provider_selection: ProviderSelection,
        thinking: str | bool | None,
    ) -> dict[str, object]:
        self.calls.append(
            (
                "agent",
                prompt,
                system_message,
                messages,
                tools,
                provider_selection,
                thinking,
            )
        )
        return {"type": "text", "content": "ok"}


class FakeRuntimeGateway:
    def __init__(self, version: str, llm_ready: bool):
        self._version = version
        self._llm_ready = llm_ready

    def get_version(self) -> str:
        return self._version

    def is_llm_ready(self) -> bool:
        return self._llm_ready


class FakeProviderResolverGateway:
    def resolve(self, provider_alias: str) -> ProviderSelection:
        if provider_alias == "medium":
            return ProviderSelection(
                alias="medium",
                provider="groq",
                model="llama-3.3-70b-versatile",
            )
        return ProviderSelection(alias=provider_alias, provider="groq", model=provider_alias)


class FakeResolveProviderUseCase:
    def __init__(self):
        self.called_with: list[str] = []

    def execute(self, provider_alias: str) -> ProviderSelection:
        self.called_with.append(provider_alias)
        return ProviderSelection(
            alias=provider_alias,
            provider="gemini",
            model="gemini-3.1-flash-lite-preview",
        )


def test_build_prompt_doc_mode_returns_content():
    use_case = BuildPromptUseCase()
    data = FakeAnalysisInput(content="def main(): pass", language="python", provider="groq", mode="doc")

    assert use_case.execute(data) == "def main(): pass"


def test_build_prompt_question_mode_requires_question():
    use_case = BuildPromptUseCase()
    data = FakeAnalysisInput(content="texte", language="text", provider="groq", mode="question", question=None)

    with pytest.raises(InvalidAnalysisRequestError):
        use_case.execute(data)


@pytest.mark.asyncio
async def test_analyze_stream_use_case_delegates_to_gateway():
    gateway = FakeLLMGateway()
    resolve_provider_use_case = FakeResolveProviderUseCase()
    use_case = AnalyzeStreamUseCase(
        llm_gateway=gateway,
        build_prompt_use_case=BuildPromptUseCase(),
        resolve_provider_use_case=resolve_provider_use_case,
    )
    data = FakeAnalysisInput(
        content="mon document",
        language="text",
        provider="gemini",
        mode=Mode("question"),
        question="quelle info?",
    )

    chunks = [chunk async for chunk in use_case.execute(data)]

    assert chunks == ["chunk-1", "chunk-2"]
    assert gateway.calls[0] == ("system", "question", "text")
    assert gateway.calls[1][0] == "stream"
    assert "document :" in gateway.calls[1][1]
    assert "question : quelle info?" in gateway.calls[1][1]
    assert gateway.calls[1][3] == "question"
    assert gateway.calls[1][4].alias == "gemini"
    assert gateway.calls[1][4].provider == "gemini"
    assert gateway.calls[1][4].model == "gemini-3.1-flash-lite-preview"
    assert gateway.calls[1][5] is None
    assert gateway.calls[1][6] is False
    assert resolve_provider_use_case.called_with == ["gemini"]


def test_health_check_use_case_builds_expected_payload():
    use_case = HealthCheckUseCase(runtime_gateway=FakeRuntimeGateway(version="0.1.0", llm_ready=True))

    result = use_case.execute()

    assert result.status == "healthy"
    assert result.version == "0.1.0"
    assert result.llm_ready is True


def test_resolve_provider_use_case_returns_provider_selection():
    use_case = ResolveProviderUseCase(provider_resolver_gateway=FakeProviderResolverGateway())

    result = use_case.execute("medium")

    assert result.alias == "medium"
    assert result.provider == "groq"
    assert result.model == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_execute_agent_call_use_case_uses_resolved_provider():
    gateway = FakeLLMGateway()
    resolve_provider_use_case = FakeResolveProviderUseCase()
    use_case = ExecuteAgentCallUseCase(
        llm_gateway=gateway,
        resolve_provider_use_case=resolve_provider_use_case,
    )

    result = await use_case.execute(
        prompt="hello",
        system_message="system",
        provider="gemini",
        thinking="off",
    )

    assert result["type"] == "text"
    assert result["content"] == "ok"
    assert gateway.calls[-1][0] == "agent"
    assert gateway.calls[-1][5].provider == "gemini"
    assert gateway.calls[-1][5].model == "gemini-3.1-flash-lite-preview"
    assert resolve_provider_use_case.called_with[-1] == "gemini"


@pytest.mark.asyncio
async def test_generate_full_response_use_case_aggregates_stream_with_resolution():
    gateway = FakeLLMGateway()
    resolve_provider_use_case = FakeResolveProviderUseCase()
    use_case = GenerateFullResponseUseCase(
        llm_gateway=gateway,
        resolve_provider_use_case=resolve_provider_use_case,
    )

    result = await use_case.execute(
        prompt="hello",
        system_message="system",
        mode="question",
        provider="gemini",
        thinking="off",
        json_format=True,
    )

    assert result == "chunk-1chunk-2"
    assert gateway.calls[-1][0] == "stream"
    assert gateway.calls[-1][3] == "question"
    assert gateway.calls[-1][4].provider == "gemini"
    assert gateway.calls[-1][5] == "off"
    assert gateway.calls[-1][6] is True
    assert resolve_provider_use_case.called_with[-1] == "gemini"
