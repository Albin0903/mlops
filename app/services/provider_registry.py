# Configuration des modeles par provider (version free tier)
# Configs recommandees pour Pedantix :
#   rapide + qualite : --provider groq --sub-provider ollama-small
#   sans API cloud   : --provider ollama --sub-provider ollama-small
PROVIDER_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-3.1-flash-lite-preview",
    "ollama": "qwen3.5:9b",  # Modele local par defaut
    "ollama-medium": "qwen3.5:9b",  # Alias local moyen
    "ollama-small": "qwen3.5:2b",  # Modele local leger
    "ollama-mini": "qwen3.5:0.8b",  # Modele local tres leger
    "ollama-llama3": "llama3.1:8b",  # Modele local Llama 3.1
    "gemma4-e2b": "gemma4:e2b",
    "gemma4-e4b": "gemma4:e4b",
    "gemma4-26b": "gemma4:26b",
    "instant": "llama-3.1-8b-instant",
    "medium": "llama-3.3-70b-versatile",
    "gpt": "openai/gpt-oss-120b",
}


def resolve_provider_name(provider: str, model: str) -> str:
    """Determine le provider reel a partir de l'alias et du modele."""
    provider_lower = provider.lower()
    model_lower = model.lower()

    if "gemini" in provider_lower or "gemini" in model_lower:
        return "gemini"
    if "ollama" in provider_lower or model_lower.startswith(("qwen", "gemma")):
        return "ollama"
    return "groq"


def get_supported_providers() -> tuple[str, ...]:
    return tuple(PROVIDER_MODELS.keys())
