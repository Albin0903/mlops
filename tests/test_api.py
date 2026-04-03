"""
tests/test_api.py — tests d'integration des endpoints fastapi.
verifie le comportement complet de l'api avec mocking du service llm.
"""

from unittest.mock import Mock, patch

import pytest

from app.application.errors import InvalidAnalysisRequestError


@pytest.mark.asyncio
async def test_analyze_doc_mode_returns_streaming(client, mock_groq_api_key, mock_streaming_response):
    """le endpoint /analyze doit retourner une reponse en streaming pour le mode doc"""
    with patch("app.api.routes.analysis.get_analyze_stream_use_case") as get_use_case:
        mock_use_case = Mock()
        mock_use_case.execute.return_value = mock_streaming_response()
        get_use_case.return_value = mock_use_case

        response = await client.post(
            "/analyze/", json={"content": "def hello(): pass", "language": "python", "mode": "doc"}
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert response.text == "Bonjour le monde"
        mock_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_question_mode_returns_streaming(client, mock_groq_api_key, mock_streaming_response):
    """le endpoint /analyze doit fonctionner en mode question"""
    with patch("app.api.routes.analysis.get_analyze_stream_use_case") as get_use_case:
        mock_use_case = Mock()
        mock_use_case.execute.return_value = mock_streaming_response()
        get_use_case.return_value = mock_use_case

        response = await client.post(
            "/analyze/",
            json={
                "content": "le projet utilise terraform",
                "language": "text",
                "mode": "question",
                "question": "quel outil est utilise ?",
            },
        )

        assert response.status_code == 200
        assert response.text == "Bonjour le monde"
        mock_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_question_mode_without_question_returns_400(client, mock_groq_api_key):
    """le mode question sans question doit retourner une erreur 400"""
    with patch("app.api.routes.analysis.get_analyze_stream_use_case") as get_use_case:
        mock_use_case = Mock()
        mock_use_case.execute.side_effect = InvalidAnalysisRequestError(
            "la question est obligatoire en mode 'question'"
        )
        get_use_case.return_value = mock_use_case

        response = await client.post(
            "/analyze/",
            json={"content": "du texte", "language": "text", "mode": "question"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "question" in data["detail"].lower()


@pytest.mark.asyncio
async def test_analyze_invalid_mode_returns_422(client, mock_groq_api_key):
    """un mode invalide doit retourner une erreur 422 (validation pydantic)"""
    response = await client.post("/analyze/", json={"content": "code", "mode": "invalid_mode"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_empty_content_returns_422(client, mock_groq_api_key):
    """un contenu vide doit retourner une erreur 422"""
    response = await client.post("/analyze/", json={"content": "", "mode": "doc"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_missing_content_returns_422(client, mock_groq_api_key):
    """le champ content est obligatoire"""
    response = await client.post("/analyze/", json={"mode": "doc"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_default_values(client, mock_groq_api_key, mock_streaming_response):
    """les valeurs par defaut (mode=doc, language=python) doivent etre appliquees"""
    with patch("app.api.routes.analysis.get_analyze_stream_use_case") as get_use_case:
        mock_use_case = Mock()
        mock_use_case.execute.return_value = mock_streaming_response()
        get_use_case.return_value = mock_use_case

        response = await client.post("/analyze/", json={"content": "def test(): pass"})

        assert response.status_code == 200
        execute_arg = mock_use_case.execute.call_args.args[0]
        assert execute_arg.mode.value == "doc"
        assert execute_arg.language == "python"
        assert execute_arg.provider == "gemma4b"
