"""
configuration partagee pour les tests.
fixtures reutilisables : client http async, mock du service llm.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    """client http asynchrone pour tester les endpoints fastapi"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_groq_api_key():
    """simule la presence d'une cle api groq dans la configuration"""
    with patch("app.core.config.settings.groq_api_key", "fake-test-key"):
        yield


@pytest.fixture
def mock_no_groq_api_key():
    """simule l'absence de cle api groq"""
    with patch("app.core.config.settings.groq_api_key", None):
        yield


@pytest.fixture
def mock_streaming_response():
    """simule une reponse llm en streaming (3 chunks)"""
    async def fake_stream(*args, **kwargs):
        chunks = ["Bonjour", " le", " monde"]
        for text in chunks:
            yield text

    return fake_stream
