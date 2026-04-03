from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.application.errors import InvalidAnalysisRequestError
from app.domain.analysis import AnalysisInput, AnalysisMode
from app.infrastructure.composition import get_analyze_stream_use_case
from app.schemas.analysis import AnalysisRequest

router = APIRouter()

# regle d'ingenierie : streaming asynchrone pour une experience utilisateur fluide


@router.post("/")
async def analyze_code(request: AnalysisRequest):
    """endpoint principal pour l'analyse de code ou generation de doc en streaming"""
    analysis_input = AnalysisInput(
        content=request.content,
        language=request.language,
        mode=AnalysisMode(request.mode),
        provider=request.provider,
        question=request.question,
    )

    use_case = get_analyze_stream_use_case()
    try:
        stream = use_case.execute(analysis_input)
    except InvalidAnalysisRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(stream, media_type="text/event-stream")
