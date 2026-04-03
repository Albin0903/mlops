"""End-to-end smoke scenario for the API-first flow."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@dataclass(frozen=True, slots=True)
class FakeHealthStatus:
    status: str
    version: str
    llm_ready: bool


class FakeHealthCheckUseCase:
    def execute(self) -> FakeHealthStatus:
        return FakeHealthStatus(status="healthy", version="9.9.9", llm_ready=True)


class FakeAnalyzeStreamUseCase:
    def __init__(self):
        self.last_input = None

    def execute(self, analysis_input):
        self.last_input = analysis_input

        async def _stream():
            yield "alpha"
            yield "beta"

        return _stream()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_api_smoke_flow_health_then_analyze():
    fake_health_use_case = FakeHealthCheckUseCase()
    fake_analyze_use_case = FakeAnalyzeStreamUseCase()

    with (
        patch("app.api.routes.health.get_health_check_use_case", return_value=fake_health_use_case),
        patch("app.api.routes.analysis.get_analyze_stream_use_case", return_value=fake_analyze_use_case),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            root_response = await client.get("/")
            assert root_response.status_code == 200
            assert "message" in root_response.json()

            health_response = await client.get("/health/")
            assert health_response.status_code == 200
            assert health_response.json() == {
                "status": "healthy",
                "version": "9.9.9",
                "llm_ready": True,
            }

            analyze_response = await client.post(
                "/analyze/",
                json={
                    "content": "def f():\n    return 1",
                    "language": "python",
                    "mode": "doc",
                    "provider": "gemma4b",
                },
            )
            assert analyze_response.status_code == 200
            assert "text/event-stream" in analyze_response.headers["content-type"]
            assert analyze_response.text == "alphabeta"
            assert fake_analyze_use_case.last_input.provider == "gemma4b"
            assert fake_analyze_use_case.last_input.mode.value == "doc"
