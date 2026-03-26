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
        with patch("app.services.llm_service.get_provider", return_value=None), patch(
            "app.services.llm_service.settings"
        ) as mock_settings:
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
        with patch("app.services.llm_service.get_provider", return_value=None), patch(
            "app.services.llm_service.settings"
        ) as mock_settings:
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
            async def stream_response(self, prompt, system_message, model):
                for text in ["Hello", " World", "!"]:
                    yield text, 1, 1

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()), patch(
            "app.services.llm_service.settings"
        ) as mock_settings:
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
            async def stream_response(self, prompt, system_message, model):
                if False:
                    yield "", 0, 0
                raise Exception("connection timeout")

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()), patch(
            "app.services.llm_service.settings"
        ) as mock_settings:
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
            async def stream_response(self, prompt, system_message, model):
                yield "Hello", 1, 1
                yield "", 0, 0
                yield " World", 1, 1

        with patch("app.services.llm_service.get_provider", return_value=FakeProvider()), patch(
            "app.services.llm_service.settings"
        ) as mock_settings:
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
