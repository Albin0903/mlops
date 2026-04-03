"""
tests/test_llm_service.py — tests du service llm avec mocking de l'api groq et gemini.
aucun appel reel n'est effectue.
"""

from unittest.mock import patch

import pytest

from app.services.llm.ollama import (
    _extract_chunk_content,
    _parse_model_size_billion,
    _select_num_ctx,
    _split_thinking_content,
)
from app.services.llm_service import PROVIDER_MODELS, SYSTEM_PROMPTS, LLMService


class TestSystemPrompts:
    """tests sur la generation des prompts systeme"""

    def test_doc_prompt_contains_language(self):
        """le prompt doc doit inclure le langage specifie"""
        service = LLMService.__new__(LLMService)
        prompt = service.get_system_prompt("doc", "python")
        assert "python" in prompt

    def test_question_prompt_contains_language(self):
        """le prompt question doit inclure le langage specifie"""
        service = LLMService.__new__(LLMService)
        prompt = service.get_system_prompt("question", "javascript")
        assert "javascript" in prompt

    def test_doc_prompt_requires_markdown(self):
        """le prompt doc doit exiger une reponse en markdown"""
        prompt = SYSTEM_PROMPTS["doc"].format(language="python")
        assert "markdown" in prompt

    def test_question_prompt_requires_reasoned_answer(self):
        """le prompt question doit exiger une reponse argumentee"""
        prompt = SYSTEM_PROMPTS["question"].format(language="text")
        assert "argumentee" in prompt

    def test_invalid_mode_raises_key_error(self):
        """un mode inexistant doit lever une KeyError"""
        service = LLMService.__new__(LLMService)
        with pytest.raises(KeyError):
            service.get_system_prompt("invalid_mode", "python")


class TestProviderConfig:
    """tests sur la configuration multi-provider"""

    def test_provider_models_defined(self):
        """chaque provider doit avoir un modele associe"""
        assert "groq" in PROVIDER_MODELS
        assert "gemini" in PROVIDER_MODELS
        assert "ollama-mini" in PROVIDER_MODELS
        assert PROVIDER_MODELS["ollama-mini"] == "qwen3.5:0.8b"
        assert "ollama" in PROVIDER_MODELS
        assert PROVIDER_MODELS["ollama"] == "gemma4:e4b"
        assert PROVIDER_MODELS["gemma4b"] == "gemma4:e4b"
        assert PROVIDER_MODELS["gemma4-e2b"] == "gemma4:e2b"
        assert PROVIDER_MODELS["gemma4-e4b"] == "gemma4:e4b"


class TestStreamingResponse:
    """tests du streaming groq avec mocking complet"""

    @pytest.mark.asyncio
    async def test_get_full_response_aggregates_stream(self):
        """le helper get_full_response doit concatener tous les chunks du stream"""
        service = LLMService.__new__(LLMService)

        async def mock_streaming_response(*args, **kwargs):
            for chunk in ["alpha", " beta", " gamma"]:
                yield chunk

        service.get_streaming_response = mock_streaming_response

        result = await service.get_full_response("prompt", "system", provider="gemini")

        assert result == "alpha beta gamma"

    @pytest.mark.asyncio
    async def test_streaming_without_groq_key(self):
        """sans cle api groq, le service doit retourner un message d'erreur"""
        with (
            patch("app.services.llm_service.get_provider", return_value=None),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "provider groq" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_without_gemini_key(self):
        """sans cle api gemini, le service doit retourner un message d'erreur"""
        with (
            patch("app.services.llm_service.get_provider", return_value=None),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="gemini"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "provider gemini" in chunks[0]

    @pytest.mark.asyncio
    async def test_groq_streaming_returns_chunks(self):
        """avec une cle api groq, le service doit streamer les chunks"""

        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                for text in ["Hello", " World", "!"]:
                    yield text, 1, 1

        with (
            patch("app.services.llm_service.get_provider", return_value=FakeProvider()),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World", "!"]

    @pytest.mark.asyncio
    async def test_streaming_handles_exception_gracefully(self):
        """en cas d'erreur reseau, le service doit retourner un message d'erreur"""

        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                if False:
                    yield "", 0, 0
                raise Exception("connection timeout")

        with (
            patch("app.services.llm_service.get_provider", return_value=FakeProvider()),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "[Erreur technique" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_skips_empty_chunks(self):
        """les chunks sans contenu (delta.content=None) doivent etre ignores"""

        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                yield "Hello", 1, 1
                yield "", 0, 0
                yield " World", 1, 1

        with (
            patch("app.services.llm_service.get_provider", return_value=FakeProvider()),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World"]


class TestOllamaChunkParsing:
    def test_extract_chunk_content_supports_chat_payload(self):
        payload = {"message": {"role": "assistant", "content": "Bonjour"}}

        assert _extract_chunk_content(payload) == "Bonjour"

    def test_extract_chunk_content_supports_generate_payload(self):
        payload = {"response": "Bonjour"}

        assert _extract_chunk_content(payload) == "Bonjour"

    def test_split_thinking_content(self):
        thoughts, visible = _split_thinking_content("<think>je réfléchis</think>Réponse finale")

        assert thoughts == ["je réfléchis"]
        assert visible == "Réponse finale"


class TestOllamaContextSizing:
    def test_parse_model_size_billion(self):
        assert _parse_model_size_billion("qwen3.5:2b") == 2.0
        assert _parse_model_size_billion("qwen3.5:9b") == 9.0

    def test_select_num_ctx_for_small_model_on_6gb(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 6144)

        assert _select_num_ctx("qwen3.5:2b") == 8192

    def test_select_num_ctx_for_9b_model_on_6gb(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 6144)

        assert _select_num_ctx("qwen3.5:9b") == 4096

    def test_parse_model_size_gemma4_expert_tag(self):
        assert _parse_model_size_billion("gemma4:e4b") == 4.0
        assert _parse_model_size_billion("gemma4:e2b") == 2.0

    def test_select_num_ctx_for_gemma4_e4b(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.ollama._detect_total_vram_mb", lambda: 6144)

        assert _select_num_ctx("gemma4:e4b") == 8192


class TestProviderResolution:
    """tests sur la resolution du provider reel"""

    def test_resolve_gemini(self):
        service = LLMService.__new__(LLMService)
        assert service._resolve_provider("gemini", "gemini-3.1-flash-lite-preview") == "gemini"

    def test_resolve_ollama_variants(self):
        service = LLMService.__new__(LLMService)
        assert service._resolve_provider("ollama", "qwen3.5:9b") == "ollama"
        assert service._resolve_provider("ollama-small", "qwen3.5:2b") == "ollama"
        assert service._resolve_provider("gemma4b", "gemma4:e4b") == "ollama"

    def test_resolve_groq_default(self):
        service = LLMService.__new__(LLMService)
        assert service._resolve_provider("groq", "llama-3.1-8b-instant") == "groq"


class TestExecuteAgentCall:
    """tests du execute_agent_call avec mocking"""

    @pytest.mark.asyncio
    async def test_agent_call_returns_text(self):
        """un appel agent sans tool_calls doit retourner du texte"""

        class FakeProvider:
            async def execute_agent_call(self, messages, model, tools, thinking=None):
                return {"type": "text", "content": "Analyse en cours"}

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()):
            service = LLMService.__new__(LLMService)
            result = await service.execute_agent_call(prompt="test", system_message="system", provider="groq")
            assert result["type"] == "text"
            assert result["content"] == "Analyse en cours"

    @pytest.mark.asyncio
    async def test_agent_call_returns_tool_calls(self):
        """un appel agent avec tool_calls doit retourner les appels d'outils"""

        class FakeProvider:
            async def execute_agent_call(self, messages, model, tools, thinking=None):
                return {
                    "type": "tool_calls",
                    "calls": [{"name": "get_game_state", "args": {}}],
                }

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()):
            service = LLMService.__new__(LLMService)
            result = await service.execute_agent_call(
                prompt="test", system_message="system", tools=[{"type": "function"}], provider="groq"
            )
            assert result["type"] == "tool_calls"
            assert len(result["calls"]) == 1
            assert result["calls"][0]["name"] == "get_game_state"

    @pytest.mark.asyncio
    async def test_agent_call_uses_resolved_provider_and_model(self):
        class FakeProvider:
            async def execute_agent_call(self, messages, model, tools, thinking=None):
                return {"type": "text", "content": model}

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()) as mocked_get_provider:
            service = LLMService.__new__(LLMService)
            result = await service.execute_agent_call(
                prompt="test",
                system_message="system",
                provider="medium",
                resolved_provider="groq",
                resolved_model="llama-3.3-70b-versatile",
            )

            assert result["type"] == "text"
            assert result["content"] == "llama-3.3-70b-versatile"
            mocked_get_provider.assert_called_once_with("groq")


class FakeObservabilityGateway:
    def __init__(self):
        self.start_calls: list[dict] = []
        self.error_mark_calls: list[dict] = []
        self.end_calls: list[dict] = []
        self.success_calls: list[dict] = []
        self.error_calls: list[dict] = []

    def start_generation(self, **kwargs):
        self.start_calls.append(kwargs)
        return "generation"

    def mark_generation_error(self, generation, error_message: str):
        self.error_mark_calls.append({"generation": generation, "error_message": error_message})

    def end_generation(self, **kwargs):
        self.end_calls.append(kwargs)

    def record_success(self, **kwargs):
        self.success_calls.append(kwargs)

    def record_error(self, **kwargs):
        self.error_calls.append(kwargs)


class TestObservabilityGatewayIntegration:
    @pytest.mark.asyncio
    async def test_streaming_reports_success_to_observability_gateway(self):
        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                yield "Hello", 11, 13

        fake_observability = FakeObservabilityGateway()
        with (
            patch("app.services.llm_service.get_provider", return_value=FakeProvider()),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = True
            service = LLMService(observability_gateway=fake_observability)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

        assert chunks == ["Hello"]
        assert len(fake_observability.start_calls) == 1
        assert fake_observability.start_calls[0]["provider"] == "groq"
        assert len(fake_observability.success_calls) == 1
        usage = fake_observability.success_calls[0]["usage"]
        assert usage.input_tokens == 11
        assert usage.output_tokens == 13
        assert len(fake_observability.end_calls) == 1
        assert fake_observability.end_calls[0]["generation"] == "generation"

    @pytest.mark.asyncio
    async def test_streaming_reports_error_to_observability_gateway(self):
        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                raise RuntimeError("network down")
                yield ""  # pragma: no cover

        fake_observability = FakeObservabilityGateway()
        with (
            patch("app.services.llm_service.get_provider", return_value=FakeProvider()),
            patch("app.services.llm_service.settings") as mock_settings,
        ):
            mock_settings.langfuse_enabled = False
            service = LLMService(observability_gateway=fake_observability)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert "[Erreur technique" in chunks[0]
        assert len(fake_observability.error_mark_calls) == 1
        assert len(fake_observability.error_calls) == 1
        assert fake_observability.error_calls[0]["error_message"] == "network down"
        assert fake_observability.success_calls == []


class TestProviderGetterInjection:
    @pytest.mark.asyncio
    async def test_streaming_uses_injected_provider_getter(self):
        class FakeProvider:
            async def stream_response(self, prompt, system_message, model, **kwargs):
                yield "ok", 1, 2

        calls: list[str] = []

        def fake_get_provider(provider_name: str):
            calls.append(provider_name)
            return FakeProvider()

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.langfuse_enabled = False
            service = LLMService(provider_getter=fake_get_provider)

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="gemini"):
                chunks.append(chunk)

        assert chunks == ["ok"]
        assert calls == ["gemini"]
