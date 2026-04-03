# Configuration des modeles par provider (version free tier)
# Configs recommandees pour Pedantix :
#   rapide + qualite : --provider groq --sub-provider ollama-small
#   sans API cloud   : --provider gemma4b --sub-provider ollama-small
CANONICAL_PROVIDER_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-3.1-flash-lite-preview",
    "ollama": "gemma4:e4b",  # Modele local par defaut
    "ollama-medium": "qwen3.5:9b",  # Alias local moyen
    "ollama-small": "qwen3.5:2b",  # Alias local leger
    "ollama-mini": "qwen3.5:0.8b",  # Alias local tres leger
    "ollama-llama3": "llama3.1:8b",  # Alias local Llama 3.1
    "gemma4-e2b": "gemma4:e2b",
    "gemma4-e4b": "gemma4:e4b",
    "gemma4-26b": "gemma4:26b",
    "instant": "llama-3.1-8b-instant",
    "medium": "llama-3.3-70b-versatile",
    "gpt": "openai/gpt-oss-120b",
}

PROVIDER_ALIAS_REDIRECTS = {
    "default": "ollama",
    "local": "ollama",
    "gemma4b": "gemma4-e4b",
    "gemma4-4b": "gemma4-e4b",
    "gemma4:e4b": "gemma4-e4b",
    "gemma4-2b": "gemma4-e2b",
    "gemma4:e2b": "gemma4-e2b",
    "qwen9b": "ollama-medium",
    "qwen3.5-9b": "ollama-medium",
    "qwen2b": "ollama-small",
    "qwen3.5-2b": "ollama-small",
    "qwen0.8b": "ollama-mini",
    "qwen3.5-0.8b": "ollama-mini",
    "llama3-local": "ollama-llama3",
}

PROVIDER_MODELS = dict(CANONICAL_PROVIDER_MODELS)
for alias, canonical_alias in PROVIDER_ALIAS_REDIRECTS.items():
    canonical_model = CANONICAL_PROVIDER_MODELS.get(canonical_alias)
    if canonical_model:
        PROVIDER_MODELS[alias] = canonical_model


def resolve_provider_alias(provider: str) -> str:
    """Normalise un alias provider/modele vers une cle supportee."""
    normalized = provider.strip().lower()
    return PROVIDER_ALIAS_REDIRECTS.get(normalized, normalized)


def resolve_provider_name(provider: str, model: str) -> str:
    """Determine le provider reel a partir de l'alias et du modele."""
    provider_lower = resolve_provider_alias(provider)
    model_lower = model.lower().strip()

    if "gemini" in provider_lower or "gemini" in model_lower:
        return "gemini"
    if "ollama" in provider_lower or model_lower.startswith(("qwen", "gemma", "llama3")):
        return "ollama"
    return "groq"


def get_supported_providers() -> tuple[str, ...]:
    return tuple(sorted(PROVIDER_MODELS.keys()))
