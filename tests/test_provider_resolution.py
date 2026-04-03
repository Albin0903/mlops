"""Tests unitaires de l'adapter de resolution provider."""

from app.infrastructure.adapters.provider_resolver_gateway import RegistryProviderResolverGateway


def test_registry_provider_resolver_gateway_resolves_groq_alias():
    gateway = RegistryProviderResolverGateway()

    selection = gateway.resolve("medium")

    assert selection.alias == "medium"
    assert selection.provider == "groq"
    assert selection.model == "llama-3.3-70b-versatile"


def test_registry_provider_resolver_gateway_resolves_ollama_alias():
    gateway = RegistryProviderResolverGateway()

    selection = gateway.resolve("ollama-small")

    assert selection.alias == "ollama-small"
    assert selection.provider == "ollama"
    assert selection.model == "qwen3.5:2b"


def test_registry_provider_resolver_gateway_falls_back_to_alias_as_model():
    gateway = RegistryProviderResolverGateway()

    selection = gateway.resolve("custom-model-id")

    assert selection.alias == "custom-model-id"
    assert selection.provider == "groq"
    assert selection.model == "custom-model-id"
