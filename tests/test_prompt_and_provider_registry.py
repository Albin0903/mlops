"""Tests unitaires des modules extraits (prompts et registry providers)."""

from app.services.prompt_manager import SYSTEM_PROMPTS, build_system_prompt
from app.services.provider_registry import (
    PROVIDER_MODELS,
    get_supported_providers,
    resolve_provider_alias,
    resolve_provider_name,
)


def test_build_system_prompt_injects_language():
    prompt = build_system_prompt("doc", "python")

    assert "python" in prompt
    assert "markdown" in prompt


def test_system_prompts_contains_question_mode():
    assert "question" in SYSTEM_PROMPTS


def test_provider_registry_contains_gemma_aliases():
    assert PROVIDER_MODELS["ollama"] == "gemma4:e4b"
    assert PROVIDER_MODELS["gemma4b"] == "gemma4:e4b"
    assert PROVIDER_MODELS["gemma4-e2b"] == "gemma4:e2b"
    assert PROVIDER_MODELS["gemma4-e4b"] == "gemma4:e4b"


def test_resolve_provider_alias_normalizes_shortcuts():
    assert resolve_provider_alias("Gemma4B") == "gemma4-e4b"
    assert resolve_provider_alias("qwen2b") == "ollama-small"


def test_resolve_provider_name_routes_ollama_models():
    assert resolve_provider_name("ollama-small", "qwen3.5:2b") == "ollama"
    assert resolve_provider_name("gemma4b", "gemma4:e4b") == "ollama"


def test_resolve_provider_name_routes_gemini():
    assert resolve_provider_name("gemini", "gemini-3.1-flash-lite-preview") == "gemini"


def test_get_supported_providers_contains_core_aliases():
    providers = get_supported_providers()

    assert "groq" in providers
    assert "gemini" in providers
    assert "ollama-small" in providers
    assert "gemma4b" in providers
    assert "gemma4-e4b" in providers
