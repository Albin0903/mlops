from pydantic_settings import BaseSettings, SettingsConfigDict

# regle : gestion centralisee des secrets et configurations


class Settings(BaseSettings):
    """configuration de l'application via variables d'environnement"""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "llm-code-analyzer"
    version: str = "0.1.0"
    api_v1_str: str = "/api/v1"

    # credentials aws (vpc, iam, s3 backend)
    aws_id_key: str | None = None
    aws_secret_key: str | None = None

    # cles api llm (a configurer dans .env)
    openai_api_key: str | None = None
    mistral_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    # observabilite langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def langfuse_enabled(self) -> bool:
        """langfuse est active si les deux cles sont configurees"""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


settings = Settings()
