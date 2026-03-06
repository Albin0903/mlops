from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.analysis import AnalysisRequest
from app.services.llm_service import llm_service

router = APIRouter()

# regle d'ingenierie : streaming asynchrone pour une experience utilisateur fluide

@router.post("/")
async def analyze_code(request: AnalysisRequest):
    """endpoint principal pour l'analyse de code ou generation de doc en streaming"""

    # recuperation du prompt systeme optimise depuis le service
    system_message = llm_service.get_system_prompt(request.mode, request.language)

    # construction du prompt utilisateur selon le mode
    if request.mode == "doc":
        prompt = request.content
    else:
        if not request.question:
            raise HTTPException(status_code=400, detail="la question est obligatoire en mode 'question'")
        prompt = f"document :\n{request.content}\n\nquestion : {request.question}"

    # retour d'une reponse en streaming vers le client (provider configurable)
    return StreamingResponse(
        llm_service.get_streaming_response(prompt, system_message, mode=request.mode, provider=request.provider),
        media_type="text/event-stream"
    )
