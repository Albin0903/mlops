"""
tests/test_llm_service.py — tests du service llm avec mocking de l'api groq.
aucun appel reel a groq n'est effectue.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_service import LLMService, SYSTEM_PROMPTS


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

    def test_question_prompt_requires_factual_answer(self):
        """le prompt question doit exiger une reponse factuelle"""
        prompt = SYSTEM_PROMPTS["question"].format(language="text")
        assert "factuelle" in prompt

    def test_invalid_mode_raises_key_error(self):
        """un mode inexistant doit lever une KeyError"""
        service = LLMService.__new__(LLMService)
        with pytest.raises(KeyError):
            service.get_system_prompt("invalid_mode", "python")


class TestStreamingResponse:
    """tests du streaming avec mocking complet de groq"""

    @pytest.mark.asyncio
    async def test_streaming_without_api_key(self):
        """sans cle api, le service doit retourner un message d'erreur"""
        with patch("app.services.llm_service.settings.groq_api_key", None):
            service = LLMService.__new__(LLMService)
            chunks = []
            async for chunk in service.get_streaming_response("test", "system"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "cle api groq" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_with_api_key_returns_chunks(self):
        """avec une cle api, le service doit streamer les chunks du llm"""
        # creer des mock chunks simulant la reponse groq
        mock_chunks = []
        for text in ["Hello", " World", "!"]:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = text
            mock_chunks.append(mock_chunk)

        # creer un async iterator pour simuler le stream
        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with patch("app.services.llm_service.settings.groq_api_key", "fake-key"):
            service = LLMService.__new__(LLMService)
            service.client = MagicMock()
            service._create_stream = AsyncMock(return_value=mock_stream())

            chunks = []
            async for chunk in service.get_streaming_response("test prompt", "system msg"):
                chunks.append(chunk)

            assert chunks == ["Hello", " World", "!"]

    @pytest.mark.asyncio
    async def test_streaming_handles_exception_gracefully(self):
        """en cas d'erreur reseau, le service doit retourner un message d'erreur"""
        with patch("app.services.llm_service.settings.groq_api_key", "fake-key"):
            service = LLMService.__new__(LLMService)
            service.client = MagicMock()
            service._create_stream = AsyncMock(side_effect=Exception("connection timeout"))

            chunks = []
            async for chunk in service.get_streaming_response("test", "system"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "[erreur]" in chunks[0]
            assert "connection timeout" in chunks[0]

    @pytest.mark.asyncio
    async def test_streaming_skips_empty_chunks(self):
        """les chunks sans contenu (delta.content=None) doivent etre ignores"""
        mock_chunks = []
        # chunk avec contenu
        chunk_with_content = MagicMock()
        chunk_with_content.choices = [MagicMock()]
        chunk_with_content.choices[0].delta.content = "Hello"
        mock_chunks.append(chunk_with_content)

        # chunk sans contenu (None)
        chunk_empty = MagicMock()
        chunk_empty.choices = [MagicMock()]
        chunk_empty.choices[0].delta.content = None
        mock_chunks.append(chunk_empty)

        # chunk avec contenu
        chunk_with_content2 = MagicMock()
        chunk_with_content2.choices = [MagicMock()]
        chunk_with_content2.choices[0].delta.content = " World"
        mock_chunks.append(chunk_with_content2)

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with patch("app.services.llm_service.settings.groq_api_key", "fake-key"):
            service = LLMService.__new__(LLMService)
            service.client = MagicMock()
            service._create_stream = AsyncMock(return_value=mock_stream())

            chunks = []
            async for chunk in service.get_streaming_response("test", "system"):
                chunks.append(chunk)

            # seuls les chunks avec du contenu doivent etre retournes
            assert chunks == ["Hello", " World"]
