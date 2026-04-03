from dataclasses import asdict

from fastapi import APIRouter

from app.infrastructure.composition import get_health_check_use_case

router = APIRouter()


@router.get("/")
async def get_health():
    """endpoint de sante : verifie le statut de l'api et la connectivite llm"""
    use_case = get_health_check_use_case()
    return asdict(use_case.execute())
