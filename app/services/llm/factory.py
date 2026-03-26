from typing import Optional

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

# Cache des instances de providers
PROVIDERS = {}


def get_provider(provider_name: str) -> Optional[BaseLLMProvider]:
    """Factory pour obtenir un provider LLM initialise"""

    if provider_name not in PROVIDERS:
        if provider_name == "groq" and settings.groq_api_key:
            from app.services.llm.groq import GroqProvider

            PROVIDERS[provider_name] = GroqProvider()
        elif provider_name == "gemini" and settings.gemini_api_key:
            from app.services.llm.gemini import GeminiProvider

            PROVIDERS[provider_name] = GeminiProvider()
        elif provider_name == "ollama":
            from app.services.llm.ollama import OllamaProvider

            PROVIDERS[provider_name] = OllamaProvider()
        else:
            return None

    return PROVIDERS[provider_name]
