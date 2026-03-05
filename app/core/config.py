from pydantic_settings import BaseSettings

# regle : gestion centralisee des secrets et configurations

class Settings(BaseSettings):
    """configuration de l'application via variables d'environnement"""
    project_name: str = "llm-code-analyzer"
    api_v1_str: str = "/api/v1"
    
    # credentials aws (vpc, iam, s3 backend)
    aws_id_key: str | None = None
    aws_secret_key: str | None = None
    
    # cles api llm (a configurer dans .env)
    openai_api_key: str | None = None
    mistral_api_key: str | None = None
    groq_api_key: str | None = None
    
    # observabilite
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
