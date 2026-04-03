from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


class LLMProviderRegistry:
    def __init__(self):
        # Cache des instances de providers
        self._providers: dict[str, BaseLLMProvider] = {}

    def get_provider(self, provider_name: str) -> BaseLLMProvider | None:
        """Factory pour obtenir un provider LLM initialise"""

        if provider_name not in self._providers:
            provider = self._create_provider(provider_name)
            if provider is None:
                return None
            self._providers[provider_name] = provider

        return self._providers[provider_name]

    def clear_cache(self) -> None:
        self._providers.clear()

    @staticmethod
    def _create_provider(provider_name: str) -> BaseLLMProvider | None:
        if provider_name == "groq" and settings.groq_api_key:
            from app.services.llm.groq import GroqProvider

            return GroqProvider()

        if provider_name == "gemini" and settings.gemini_api_key:
            from app.services.llm.gemini import GeminiProvider

            return GeminiProvider()

        if provider_name == "ollama":
            from app.services.llm.ollama import OllamaProvider

            return OllamaProvider()

        return None


def get_provider(provider_name: str, registry: LLMProviderRegistry | None = None) -> BaseLLMProvider | None:
    active_registry = registry or LLMProviderRegistry()
    return active_registry.get_provider(provider_name)


def clear_provider_cache(registry: LLMProviderRegistry | None = None) -> None:
    if registry is not None:
        registry.clear_cache()
