from pydantic import BaseModel, Field

# regle : validation stricte des types pour la fiabilite mlops


class AnalysisRequest(BaseModel):
    """schema de requete pour l'analyse de code ou generation de doc"""

    content: str = Field(..., min_length=1, description="le contenu (code ou texte) a traiter")
    language: str = Field("python", description="le langage de programmation concerne")
    mode: str = Field(
        "doc", pattern="^(doc|question)$", description="le mode d'utilisation : documentation ou reponse technique"
    )
    question: str | None = Field(None, description="la question specifique si le mode est 'question'")
    provider: str = Field(
        "groq", pattern="^(groq|gemini)$", description="le fournisseur llm a utiliser : groq ou gemini"
    )
