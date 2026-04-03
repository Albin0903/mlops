"""Tests unitaires ciblés des providers LLM et de l'observabilité."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest

from app.services.llm import factory as factory_module
from app.services.llm import ollama as ollama_module
from app.services.llm.factory import LLMProviderRegistry
from app.services.llm.gemini import GeminiProvider
from app.services.llm.groq import GroqProvider
from app.services.llm.ollama import OllamaProvider
from app.services.observability import LLMObservability


class _AsyncStream:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        async def _gen():
            for item in self._items:
                yield item

        return _gen()


class _FakeGroqCompletions:
    def __init__(self):
        self.calls: list[dict] = []
        self._stream_response = _AsyncStream([])
        self._agent_response: Any = None
        self._error_once: Exception | None = None

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error_once is not None:
            err = self._error_once
            self._error_once = None
            raise err
        if kwargs.get("stream"):
            return self._stream_response
        return self._agent_response


class _FakeUsage:
    prompt_tokens = 5
    completion_tokens = 7


def _build_groq_chunk(content: str):
    return SimpleNamespace(
        x_groq=SimpleNamespace(usage=_FakeUsage()),
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
    )


@pytest.mark.asyncio
async def test_groq_stream_response_supports_json_format():
    completions = _FakeGroqCompletions()
    completions._stream_response = _AsyncStream([_build_groq_chunk("hello")])
    provider = GroqProvider.__new__(GroqProvider)
    cast(Any, provider).client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="p",
            system_message="s",
            model="m",
            json_format=True,
        )
    ]

    assert out == [("hello", 5, 7)]
    assert completions.calls[0]["response_format"] == {"type": "json_object"}


def test_groq_init_uses_api_key(monkeypatch):
    groq_module = ModuleType("groq")

    class _FakeAsyncGroq:
        def __init__(self, api_key):
            self.api_key = api_key

    groq_module.AsyncGroq = _FakeAsyncGroq  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "groq", groq_module)
    monkeypatch.setattr(factory_module.settings, "groq_api_key", "groq-key")

    provider = GroqProvider()

    assert provider.client.api_key == "groq-key"


@pytest.mark.asyncio
async def test_groq_execute_agent_call_parses_tool_calls_and_retries_tool_error():
    class _ToolUseFailed(Exception):
        code = "tool_use_failed"

    tool_call = SimpleNamespace(function=SimpleNamespace(name="guess", arguments='{"x": 1}'))
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])

    completions = _FakeGroqCompletions()
    completions._agent_response = response
    completions._error_once = _ToolUseFailed("fail")

    provider = GroqProvider.__new__(GroqProvider)
    cast(Any, provider).client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = await provider.execute_agent_call(
        messages=[{"role": "user", "content": "hi"}],
        model="m",
        tools=[{"type": "function"}],
    )

    assert result == {"type": "tool_calls", "calls": [{"name": "guess", "args": {"x": 1}}]}
    assert len(completions.calls) == 2
    assert "Important:" in completions.calls[1]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_groq_execute_agent_call_raises_unexpected_error():
    completions = _FakeGroqCompletions()
    completions._error_once = RuntimeError("boom")

    provider = GroqProvider.__new__(GroqProvider)
    cast(Any, provider).client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    with pytest.raises(RuntimeError, match="boom"):
        await provider.execute_agent_call(
            messages=[{"role": "user", "content": "hi"}],
            model="m",
            tools=[{"type": "function"}],
        )


@pytest.mark.asyncio
async def test_groq_execute_agent_call_invalid_tool_json_and_text_path():
    tool_call = SimpleNamespace(function=SimpleNamespace(name="guess", arguments="not-json"))
    tool_message = SimpleNamespace(content=None, tool_calls=[tool_call])
    text_message = SimpleNamespace(content="plain", tool_calls=[])
    responses = [
        SimpleNamespace(choices=[SimpleNamespace(message=tool_message)]),
        SimpleNamespace(choices=[SimpleNamespace(message=text_message)]),
    ]

    class _SeqCompletions(_FakeGroqCompletions):
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return responses.pop(0)

    provider = GroqProvider.__new__(GroqProvider)
    cast(Any, provider).client = SimpleNamespace(chat=SimpleNamespace(completions=_SeqCompletions()))

    tool_result = await provider.execute_agent_call(
        messages=[{"role": "user", "content": "hi"}],
        model="m",
        tools=[{"type": "function"}],
    )
    text_result = await provider.execute_agent_call(
        messages=[{"role": "user", "content": "hi"}],
        model="m",
    )

    assert tool_result == {"type": "tool_calls", "calls": [{"name": "guess", "args": "not-json"}]}
    assert text_result == {"type": "text", "content": "plain"}


class _FakeTypes:
    class ThinkingConfig:
        def __init__(self, thinking_level):
            self.thinking_level = thinking_level

    class GenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Part:
        def __init__(self, *, text=None, function_call=None, function_response=None):
            self.text = text
            self.function_call = function_call
            self.function_response = function_response

        @staticmethod
        def from_text(text):
            return _FakeTypes.Part(text=text)

        @staticmethod
        def from_function_call(name, args):
            return _FakeTypes.Part(function_call=SimpleNamespace(name=name, args=args))

        @staticmethod
        def from_function_response(name, response):
            return _FakeTypes.Part(function_response=SimpleNamespace(name=name, response=response))

    class Content:
        def __init__(self, role, parts):
            self.role = role
            self.parts = parts


def _install_fake_google_genai(monkeypatch):
    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.types = _FakeTypes  # type: ignore[attr-defined]
    google_module.genai = genai_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)


def test_gemini_init_uses_api_key(monkeypatch):
    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")

    class _FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

    genai_module.Client = _FakeClient  # type: ignore[attr-defined]
    google_module.genai = genai_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setattr(factory_module.settings, "gemini_api_key", "gemini-key")

    provider = GeminiProvider()

    assert cast(Any, provider).client.api_key == "gemini-key"


@pytest.mark.asyncio
async def test_gemini_stream_response_supports_json_format(monkeypatch):
    _install_fake_google_genai(monkeypatch)

    captured = {}

    class _FakeModels:
        async def generate_content_stream(self, *, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return _AsyncStream(
                [
                    SimpleNamespace(
                        text="part",
                        usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=4),
                    )
                ]
            )

    provider = GeminiProvider.__new__(GeminiProvider)
    cast(Any, provider).client = SimpleNamespace(aio=SimpleNamespace(models=_FakeModels()))

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="hello",
            system_message="sys",
            model="gemini-model",
            json_format=True,
        )
    ]

    assert out == [("part", 3, 4)]
    assert captured["model"] == "gemini-model"
    assert captured["config"].kwargs["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_gemini_execute_agent_call_returns_tool_calls(monkeypatch):
    _install_fake_google_genai(monkeypatch)

    part = SimpleNamespace(function_call=SimpleNamespace(name="search", args={"q": "x"}))
    response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))], text="")

    class _FakeModels:
        async def generate_content(self, *, model, contents, config):
            return response

    provider = GeminiProvider.__new__(GeminiProvider)
    cast(Any, provider).client = SimpleNamespace(aio=SimpleNamespace(models=_FakeModels()))

    result = await provider.execute_agent_call(
        messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        model="gemini-model",
        tools=[
            {
                "function": {
                    "name": "search",
                    "description": "search",
                    "parameters": {"type": "object"},
                }
            }
        ],
    )

    assert result == {"type": "tool_calls", "calls": [{"name": "search", "args": {"q": "x"}}]}


@pytest.mark.asyncio
async def test_gemini_execute_agent_call_formats_assistant_and_tool_messages(monkeypatch):
    _install_fake_google_genai(monkeypatch)

    captured = {}

    class _FakeModels:
        async def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            no_tool_call_part = SimpleNamespace(function_call=None)
            return SimpleNamespace(
                candidates=[SimpleNamespace(content=SimpleNamespace(parts=[no_tool_call_part]))],
                text="plain text",
            )

    provider = GeminiProvider.__new__(GeminiProvider)
    cast(Any, provider).client = SimpleNamespace(aio=SimpleNamespace(models=_FakeModels()))

    result = await provider.execute_agent_call(
        messages=cast(
            Any,
            [
                {"role": "system", "content": "s1"},
                {"role": "system", "content": "s2"},
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "thought"},
                {
                    "role": "assistant",
                    "content": "tool-thought",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "guess",
                                "arguments": '{"x": 1}',
                            }
                        }
                    ],
                },
                {"role": "tool", "name": "guess", "content": '[{"value": 1}]'},
                {"role": "tool", "name": "broken", "content": "{bad"},
            ],
        ),
        model="gemini-model",
    )

    assert result == {"type": "text", "content": "plain text"}
    assert captured["model"] == "gemini-model"
    assert len(captured["contents"]) >= 4
    assert captured["config"].kwargs["system_instruction"] == "s1\ns2"


class _FakeResponse:
    def __init__(self, *, status_code=200, lines=None, json_data=None, text="", body=b""):
        self.status_code = status_code
        self._lines = lines or []
        self._json_data = json_data or {}
        self.text = text
        self._body = body

    async def aread(self):
        return self._body

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    def json(self):
        return self._json_data


class _FakeStreamContext:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeOllamaClient:
    def __init__(self, stream_response, fallback_response, execute_response):
        self.stream_response = stream_response
        self.fallback_response = fallback_response
        self.execute_response = execute_response
        self.stream_calls: list[dict] = []
        self.post_calls: list[dict] = []

    def stream(self, method, url, json):
        self.stream_calls.append({"method": method, "url": url, "json": json})
        return _FakeStreamContext(self.stream_response)

    async def post(self, url, json):
        self.post_calls.append({"url": url, "json": json})
        if json.get("tools"):
            return self.execute_response
        if json.get("stream") is False:
            return self.fallback_response
        return self.execute_response


@pytest.mark.asyncio
async def test_ollama_stream_response_json_mode_and_fallback(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    stream_response = _FakeResponse(status_code=200, lines=["not-json"])
    fallback_response = _FakeResponse(
        status_code=200,
        json_data={
            "message": {"content": "<think>reason</think>visible"},
            "prompt_eval_count": 9,
            "eval_count": 10,
        },
    )
    execute_response = _FakeResponse(status_code=200, json_data={"message": {"content": "unused"}})
    fake_client = _FakeOllamaClient(stream_response, fallback_response, execute_response)

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="p",
            system_message="s",
            model="qwen3.5:2b",
            thinking=True,
            json_format=True,
        )
    ]

    assert out == [("<think>reason</think>visible", 9, 10)]
    assert fake_client.stream_calls[0]["json"]["format"] == "json"
    assert fake_client.post_calls[0]["json"]["stream"] is False


@pytest.mark.asyncio
async def test_ollama_execute_agent_call_returns_tool_calls(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    execute_response = _FakeResponse(
        status_code=200,
        json_data={
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "guess", "arguments": {"x": 1}}}],
            }
        },
    )
    fake_client = _FakeOllamaClient(_FakeResponse(status_code=500), _FakeResponse(status_code=500), execute_response)

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    result = await provider.execute_agent_call(
        messages=[{"role": "user", "content": "u"}],
        model="qwen3.5:9b",
        tools=[{"type": "function"}],
        thinking="off",
    )

    assert result == {"type": "tool_calls", "calls": [{"name": "guess", "args": {"x": 1}}]}


@pytest.mark.asyncio
async def test_ollama_stream_response_handles_http_error(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    error_stream = _FakeResponse(status_code=503, body=b"backend error")
    fake_client = _FakeOllamaClient(error_stream, _FakeResponse(status_code=500), _FakeResponse(status_code=200))

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="p",
            system_message="s",
            model="qwen3.5:9b",
        )
    ]

    assert out == [("erreur ollama : 503", 0, 0)]


def test_ollama_init_sets_base_url_and_client(monkeypatch):
    class _FakeAsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", "http://localhost:11434")
    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", _FakeAsyncClient)

    provider = OllamaProvider()

    assert provider.base_url == "http://localhost:11434/api"
    assert cast(Any, provider)._client.kwargs["trust_env"] is False


def test_ollama_normalize_thinking_values():
    assert ollama_module._normalize_thinking(None) is False
    assert ollama_module._normalize_thinking(True) is True
    assert ollama_module._normalize_thinking("on") is True
    assert ollama_module._normalize_thinking("low") == "low"

    with pytest.raises(ValueError):
        ollama_module._normalize_thinking("invalid")


def test_ollama_detect_total_vram_mb_paths(monkeypatch):
    ollama_module._detect_total_vram_mb.cache_clear()
    monkeypatch.setattr(ollama_module.shutil, "which", lambda _name: None)
    assert ollama_module._detect_total_vram_mb() is None

    class _RunOK:
        stdout = "8192\n"

    ollama_module._detect_total_vram_mb.cache_clear()
    monkeypatch.setattr(ollama_module.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(ollama_module.subprocess, "run", lambda *args, **kwargs: _RunOK())
    assert ollama_module._detect_total_vram_mb() == 8192

    ollama_module._detect_total_vram_mb.cache_clear()

    def _boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(ollama_module.subprocess, "run", _boom)
    assert ollama_module._detect_total_vram_mb() is None


def test_ollama_select_num_ctx_branches(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 8192)
    assert ollama_module._select_num_ctx("qwen3.5:2b") == 12288

    monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 16384)
    assert ollama_module._select_num_ctx("qwen3.5:14b") == 8192

    monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 32768)
    assert ollama_module._select_num_ctx("qwen3.5:70b") == 4096


@pytest.mark.asyncio
async def test_ollama_stream_response_handles_data_prefix_done_and_chunk(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    stream_response = _FakeResponse(
        status_code=200,
        lines=[
            "",
            "data: [DONE]",
            "data: not-json",
            'data: {"message": {"content": "hello"}, "prompt_eval_count": 1, "eval_count": 2}',
        ],
    )
    fallback_response = _FakeResponse(status_code=200, json_data={"message": {"content": "unused"}})
    execute_response = _FakeResponse(status_code=200, json_data={"message": {"content": "unused"}})
    fake_client = _FakeOllamaClient(stream_response, fallback_response, execute_response)

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="p",
            system_message="s",
            model="qwen3.5:9b",
            thinking=False,
        )
    ]

    assert out == [("hello", 1, 2)]


@pytest.mark.asyncio
async def test_ollama_stream_response_fallback_error(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    stream_response = _FakeResponse(status_code=200, lines=[])
    fallback_response = _FakeResponse(status_code=500, text="fallback failed")
    execute_response = _FakeResponse(status_code=200, json_data={"message": {"content": "unused"}})
    fake_client = _FakeOllamaClient(stream_response, fallback_response, execute_response)

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    out = [
        chunk
        async for chunk in provider.stream_response(
            prompt="p",
            system_message="s",
            model="qwen3.5:9b",
        )
    ]

    assert out == [("erreur ollama : 500", 0, 0)]


@pytest.mark.asyncio
async def test_ollama_execute_agent_call_returns_text_cleaned(monkeypatch):
    monkeypatch.setattr("app.services.llm.ollama._select_num_ctx", lambda _model: 4096)

    execute_response = _FakeResponse(
        status_code=200,
        json_data={"message": {"content": "<think>hidden</think> visible"}},
    )
    fake_client = _FakeOllamaClient(_FakeResponse(status_code=500), execute_response, execute_response)

    provider = OllamaProvider.__new__(OllamaProvider)
    provider.base_url = "http://ollama/api"
    cast(Any, provider)._client = fake_client

    result = await provider.execute_agent_call(
        messages=[{"role": "user", "content": "u"}],
        model="qwen3.5:9b",
        thinking="off",
    )

    assert result == {"type": "text", "content": "visible"}


def test_observability_generation_lifecycle_and_metrics(monkeypatch):
    generation_calls = []

    class _FakeGeneration:
        def __init__(self):
            self.updated = []
            self.ended = []

        def update(self, **kwargs):
            self.updated.append(kwargs)

        def end(self, **kwargs):
            self.ended.append(kwargs)

    class _FakeLangfuseClient:
        def generation(self, **kwargs):
            generation_calls.append(kwargs)
            return _FakeGeneration()

    class _FakeCounter:
        def __init__(self, *_args, **_kwargs):
            self.inc_calls = []

        def labels(self, **_kwargs):
            return self

        def inc(self, value=1):
            self.inc_calls.append(value)

    class _FakeHistogram:
        def __init__(self, *_args, **_kwargs):
            self.observe_calls = []

        def labels(self, **_kwargs):
            return self

        def observe(self, value):
            self.observe_calls.append(value)

    langfuse_module = ModuleType("langfuse")
    langfuse_module.get_client = lambda: _FakeLangfuseClient()  # type: ignore[attr-defined]
    prometheus_module = ModuleType("prometheus_client")
    prometheus_module.Counter = _FakeCounter  # type: ignore[attr-defined]
    prometheus_module.Histogram = _FakeHistogram  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "langfuse", langfuse_module)
    monkeypatch.setitem(sys.modules, "prometheus_client", prometheus_module)

    from app.services.observability import PROMETHEUS_METRICS

    PROMETHEUS_METRICS.clear()

    obs = LLMObservability()
    generation = obs.start_generation(
        enabled=True,
        mode="doc",
        provider="groq",
        model="model",
        prompt="p",
        system_message="s",
    )

    assert generation is not None
    assert generation_calls[0]["name"] == "llm-doc-groq"

    obs.mark_generation_error(generation, RuntimeError("boom"))
    assert generation.updated[0]["level"] == "ERROR"

    obs.end_generation(generation, output="ok", input_tokens=1, output_tokens=2, latency_seconds=0.123)
    assert generation.ended[0]["usage"] == {"input": 1, "output": 2}

    obs.record_metrics(provider="groq", model="m", mode="doc", in_tok=2, out_tok=3, latency=0.5)


def test_factory_create_provider_branches(monkeypatch):
    class _FakeGroqProvider:
        pass

    class _FakeGeminiProvider:
        pass

    class _FakeOllamaProvider:
        pass

    groq_module = ModuleType("app.services.llm.groq")
    gemini_module = ModuleType("app.services.llm.gemini")
    ollama_module = ModuleType("app.services.llm.ollama")
    groq_module.GroqProvider = _FakeGroqProvider  # type: ignore[attr-defined]
    gemini_module.GeminiProvider = _FakeGeminiProvider  # type: ignore[attr-defined]
    ollama_module.OllamaProvider = _FakeOllamaProvider  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "app.services.llm.groq", groq_module)
    monkeypatch.setitem(sys.modules, "app.services.llm.gemini", gemini_module)
    monkeypatch.setitem(sys.modules, "app.services.llm.ollama", ollama_module)

    monkeypatch.setattr(factory_module.settings, "groq_api_key", "key")
    monkeypatch.setattr(factory_module.settings, "gemini_api_key", "key")

    assert isinstance(LLMProviderRegistry._create_provider("groq"), _FakeGroqProvider)
    assert isinstance(LLMProviderRegistry._create_provider("gemini"), _FakeGeminiProvider)
    assert isinstance(LLMProviderRegistry._create_provider("ollama"), _FakeOllamaProvider)


def test_observability_start_generation_handles_client_failure_extra(monkeypatch):
    class _FailingLangfuseClient:
        def generation(self, **_kwargs):
            raise RuntimeError("langfuse-fail")

    langfuse_module = ModuleType("langfuse")
    langfuse_module.get_client = lambda: _FailingLangfuseClient()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langfuse", langfuse_module)

    obs = LLMObservability()
    generation = obs.start_generation(
        enabled=True,
        mode="doc",
        provider="groq",
        model="model",
        prompt="p",
        system_message="s",
    )

    assert generation is None


def test_observability_end_generation_handles_exception_extra():
    class _FailingGeneration:
        def end(self, **_kwargs):
            raise RuntimeError("end-fail")

    obs = LLMObservability()
    obs.end_generation(_FailingGeneration(), output="ok", input_tokens=1, output_tokens=2, latency_seconds=0.2)


def test_observability_record_metrics_handles_exception_extra(monkeypatch):
    class _BrokenCounter:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("metrics-fail")

    class _BrokenHistogram:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("metrics-fail")

    prometheus_module = ModuleType("prometheus_client")
    prometheus_module.Counter = _BrokenCounter  # type: ignore[attr-defined]
    prometheus_module.Histogram = _BrokenHistogram  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "prometheus_client", prometheus_module)

    from app.services.observability import PROMETHEUS_METRICS

    PROMETHEUS_METRICS.clear()

    obs = LLMObservability()
    obs.record_metrics(provider="groq", model="m", mode="doc", in_tok=1, out_tok=1, latency=0.1)


def test_factory_create_provider_returns_none_without_keys_extra(monkeypatch):
    monkeypatch.setattr(factory_module.settings, "groq_api_key", None)
    monkeypatch.setattr(factory_module.settings, "gemini_api_key", None)

    assert LLMProviderRegistry._create_provider("groq") is None
    assert LLMProviderRegistry._create_provider("gemini") is None
    assert LLMProviderRegistry._create_provider("unknown") is None
