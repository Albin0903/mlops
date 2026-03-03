from fastapi import FastAPI
from app.api.routes import analysis, health

app = FastAPI(
    title="LLM Code Analyzer API",
    description="api pour l'analyse de code haute performance basee sur les llms",
    version="0.1.0"
)

# inclusion des routes
app.include_router(health.router, prefix="/health", tags=["Monitoring"])
app.include_router(analysis.router, prefix="/analyze", tags=["Analyse LLM"])

@app.get("/")
async def root():
    return {"message": "l'api llm code analyzer est opérationnelle"}
