from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import analysis, health
from app.core.config import settings

# initialisation de l'api avec les configurations centralisees
app = FastAPI(
    title=settings.project_name,
    description="api pour l'analyse de code haute performance basee sur les llms",
    version=settings.version,
)

# inclusion des routes
app.include_router(health.router, prefix="/health", tags=["Monitoring"])
app.include_router(analysis.router, prefix="/analyze", tags=["Analyse LLM"])

# configuration du monitoring prometheus
Instrumentator().instrument(app).expose(app, tags=["Monitoring"])

@app.get("/")
async def root():
    return {"message": "l'api llm code analyzer est opérationnelle"}
