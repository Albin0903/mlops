from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def get_health():
    """endpoint de sante : verifie le statut de l'api et la connectivite llm"""
    groq_configured = bool(settings.groq_api_key)
    return {
        "status": "healthy",
        "version": settings.version,
        "llm_ready": groq_configured,
    }
