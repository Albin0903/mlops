"""
tests/test_health.py — tests du endpoint /health/
verifie le statut de l'api et la detection de la connectivite llm.
"""

import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """le health check doit retourner un statut 200"""
    response = await client.get("/health/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_structure(client):
    """la reponse doit contenir status, version et llm_ready"""
    response = await client.get("/health/")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "llm_ready" in data


@pytest.mark.asyncio
async def test_health_status_is_healthy(client):
    """le statut doit etre 'healthy'"""
    response = await client.get("/health/")
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_version_format(client):
    """la version doit etre au format semver (x.y.z)"""
    response = await client.get("/health/")
    data = response.json()
    parts = data["version"].split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


@pytest.mark.asyncio
async def test_health_llm_ready_without_key(client):
    """llm_ready doit etre false si aucune cle api n'est configuree"""
    with patch("app.api.routes.health.settings.groq_api_key", None):
        response = await client.get("/health/")
        data = response.json()
        assert data["llm_ready"] is False


@pytest.mark.asyncio
async def test_health_llm_ready_with_key(client):
    """llm_ready doit etre true si la cle api est configuree"""
    with patch("app.api.routes.health.settings.groq_api_key", "fake-key"):
        response = await client.get("/health/")
        data = response.json()
        assert data["llm_ready"] is True


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """le endpoint racine doit retourner un message de confirmation"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
