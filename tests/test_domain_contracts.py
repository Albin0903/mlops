"""Tests unitaires des contrats metier (domain)."""

from app.domain.prompt import PromptSpec
from app.domain.provider import ProviderSelection
from app.domain.usage import TokenUsage


def test_provider_selection_contract_fields():
    selection = ProviderSelection(alias="medium", provider="groq", model="llama-3.3-70b-versatile")

    assert selection.alias == "medium"
    assert selection.provider == "groq"
    assert selection.model == "llama-3.3-70b-versatile"


def test_prompt_spec_contract_fields():
    prompt_spec = PromptSpec(
        mode="doc",
        language="python",
        system_message="system",
        user_prompt="def add(a, b): return a + b",
    )

    assert prompt_spec.mode == "doc"
    assert prompt_spec.language == "python"
    assert prompt_spec.system_message == "system"
    assert "def add" in prompt_spec.user_prompt


def test_token_usage_total_tokens_property():
    usage = TokenUsage(input_tokens=120, output_tokens=80)

    assert usage.input_tokens == 120
    assert usage.output_tokens == 80
    assert usage.total_tokens == 200
