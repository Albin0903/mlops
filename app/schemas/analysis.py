from pydantic import BaseModel, Field, field_validator

from app.services.provider_registry import get_supported_providers

# regle : validation stricte des types pour la fiabilite mlops


ALLOWED_MODES = {"doc", "question"}
ALLOWED_PROVIDERS = set(get_supported_providers())
PROVIDER_HELP = ", ".join(sorted(ALLOWED_PROVIDERS))


class AnalysisRequest(BaseModel):
    """schema de requete pour l'analyse de code ou generation de doc"""

    content: str = Field(..., min_length=1, description="le contenu (code ou texte) a traiter")
    language: str = Field("python", description="le langage de programmation concerne")
    mode: str = Field("doc", description="le mode d'utilisation : documentation ou reponse technique")
    question: str | None = Field(None, description="la question specifique si le mode est 'question'")
    provider: str = Field(
        "gemma4b",
        description=f"le fournisseur llm a utiliser (valeurs supportees: {PROVIDER_HELP})",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in ALLOWED_MODES:
            raise ValueError("mode invalide: attendu 'doc' ou 'question'")
        return value

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_PROVIDERS:
            raise ValueError(f"provider invalide: valeurs supportees: {PROVIDER_HELP}")
        return normalized
