"""Tests unitaires du solveur Pedantix."""

import pytest

from legacy.pedantix.client_wikipedia import resolve_wikipedia_title


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(params)
        key = (params.get("action"), params.get("titles") or params.get("search"))
        return self.responses[key]


@pytest.mark.asyncio
async def test_resolve_wikipedia_title_accepts_canonical_search_result():
    client = FakeClient(
        {
            ("query", "Panthéon Rome"): FakeResponse(
                {"query": {"pages": {"-1": {"ns": 0, "title": "Panthéon Rome", "missing": ""}}}}
            ),
            ("opensearch", "Panthéon Rome"): FakeResponse(
                [
                    "Panthéon Rome",
                    ["Panthéon (Rome)", "Panthéon romain"],
                    ["", ""],
                    ["", ""],
                ]
            ),
        }
    )

    resolved = await resolve_wikipedia_title(client, "Panthéon Rome")

    assert resolved == "Panthéon (Rome)"
    assert [call["action"] for call in client.calls] == ["query", "opensearch"]


@pytest.mark.asyncio
async def test_resolve_wikipedia_title_returns_exact_page_title():
    client = FakeClient(
        {
            ("query", "Panthéon (Rome)"): FakeResponse(
                {"query": {"pages": {"96403": {"pageid": 96403, "ns": 0, "title": "Panthéon (Rome)"}}}}
            ),
        }
    )

    resolved = await resolve_wikipedia_title(client, "Panthéon (Rome)")

    assert resolved == "Panthéon (Rome)"
    assert [call["action"] for call in client.calls] == ["query"]
