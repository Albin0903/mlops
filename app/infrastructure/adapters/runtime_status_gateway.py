from app.core.config import settings


class SettingsRuntimeStatusGateway:
    def get_version(self) -> str:
        return settings.version

    def is_llm_ready(self) -> bool:
        return bool(settings.groq_api_key)
