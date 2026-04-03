"""Tests unitaires de la factory providers LLM."""

from app.services.llm.factory import LLMProviderRegistry


class FakeProvider:
    pass


class FakeRegistry(LLMProviderRegistry):
    @staticmethod
    def _create_provider(provider_name: str):
        if provider_name == "ok":
            return FakeProvider()
        return None


def test_registry_caches_provider_instances():
    registry = FakeRegistry()

    first = registry.get_provider("ok")
    second = registry.get_provider("ok")

    assert isinstance(first, FakeProvider)
    assert first is second


def test_registry_returns_none_for_unsupported_provider():
    registry = FakeRegistry()

    result = registry.get_provider("missing")

    assert result is None


def test_registry_clear_cache_recreates_provider():
    registry = FakeRegistry()

    first = registry.get_provider("ok")
    registry.clear_cache()
    second = registry.get_provider("ok")

    assert isinstance(first, FakeProvider)
    assert isinstance(second, FakeProvider)
    assert first is not second
