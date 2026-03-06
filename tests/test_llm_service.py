"""
tests/test_llm_service.py — tests du service llm avec mocking de l'api groq et gemini.
aucun appel reel n'est effectue.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import PROVIDER_MODELS, SYSTEM_PROMPTS, TOKEN_COST, LLMService


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

    def test_token_cost_has_groq_and_gemini(self):
        """le dictionnaire de cout doit contenir groq et gemini"""
        assert "groq" in TOKEN_COST
        assert "gemini" in TOKEN_COST

    def test_each_provider_has_input_and_output_cost(self):
        """chaque provider doit avoir un cout input et output"""
        for provider in TOKEN_COST:
            assert "input" in TOKEN_COST[provider]
            assert "output" in TOKEN_COST[provider]

    def test_provider_models_defined(self):
        """chaque provider doit avoir un modele associe"""
        assert "groq" in PROVIDER_MODELS
        assert "gemini" in PROVIDER_MODELS

    def test_cost_calculation(self):
        """verification du calcul de cout pour 1000 tokens groq"""
        cost = (1000 * TOKEN_COST["groq"]["input"]) + (1000 * TOKEN_COST["groq"]["output"])
        assert cost > 0
        assert cost < 1


class TestStreamingResponse:
    """tests du streaming groq avec mocking complet"""

    @pytest.mark.asyncio
    async def test_streaming_without_groq_key(self):
        """sans cle api groq, le service doit retourner un message d'erreur"""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.groq_api_key = None
            mock_settings.gemini_api_key = "fake"  # pragma: allowlist secret
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "cle api groq" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_without_gemini_key(self):
        """sans cle api gemini, le service doit retourner un message d'erreur"""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.groq_api_key = "fake"  # pragma: allowlist secret
            mock_settings.gemini_api_key = None
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="gemini"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "cle api gemini" in chunks[0]

    @pytest.mark.asyncio
    async def test_groq_streaming_returns_chunks(self):
        """avec une cle api groq, le service doit streamer les chunks"""
        mock_chunks = []
        for text in ["Hello", " World", "!"]:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = text
            mock_chunk.x_groq = None
            mock_chunks.append(mock_chunk)

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.groq_api_key = "fake-key"  # pragma: allowlist secret
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            service.groq_client = MagicMock()
            service._create_groq_stream = AsyncMock(return_value=mock_stream())

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World", "!"]

    @pytest.mark.asyncio
    async def test_streaming_handles_exception_gracefully(self):
        """en cas d'erreur reseau, le service doit retourner un message d'erreur"""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.groq_api_key = "fake-key"  # pragma: allowlist secret
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            service.groq_client = MagicMock()
            service._create_groq_stream = AsyncMock(side_effect=Exception("connection timeout"))

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "[erreur]" in chunks[0]
            assert "connection timeout" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_skips_empty_chunks(self):
        """les chunks sans contenu (delta.content=None) doivent etre ignores"""
        mock_chunks = []
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk1.x_groq = None
        mock_chunks.append(chunk1)

        chunk_empty = MagicMock()
        chunk_empty.choices = [MagicMock()]
        chunk_empty.choices[0].delta.content = None
        chunk_empty.x_groq = None
        mock_chunks.append(chunk_empty)

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"
        chunk2.x_groq = None
        mock_chunks.append(chunk2)

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.groq_api_key = "fake-key"  # pragma: allowlist secret
            mock_settings.langfuse_enabled = False
            service = LLMService.__new__(LLMService)
            service.groq_client = MagicMock()
            service._create_groq_stream = AsyncMock(return_value=mock_stream())

            chunks = []
            async for chunk in service.get_streaming_response("test", "system", provider="groq"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World"]
