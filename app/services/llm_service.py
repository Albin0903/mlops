import os
from groq import AsyncGroq
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

# regle : resilience et streaming pour l'excellence mlops

# prompts systeme optimises pour reduire la consommation de tokens
SYSTEM_PROMPTS = {
    "doc": (
        "tu es un generateur de documentation technique. "
        "regle stricte : repond uniquement en markdown. "
        "pas d'introduction, pas de conclusion. "
        "structure : signature, description (1 ligne), parametres, retour, exemple. "
        "langue du code source : {language}."
    ),
    "question": (
        "tu es un assistant technique. "
        "regle stricte : repond uniquement a partir du document fourni. "
        "si l'information est absente, repond 'information non disponible dans le document'. "
        "reponse concise, factuelle, sans reformulation du document. "
        "langue du document : {language}."
    ),
}


class LLMService:
    def __init__(self):
        """initialisation du client groq asynchrone"""
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

    def get_system_prompt(self, mode: str, language: str) -> str:
        """retourne le prompt systeme optimise selon le mode"""
        return SYSTEM_PROMPTS[mode].format(language=language)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _create_stream(self, prompt: str, system_message: str):
        """cree le flux de completion (retryable car ne yield pas)"""
        return await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
            top_p=1,
            stream=True,
        )

    async def get_streaming_response(self, prompt: str, system_message: str):
        """genere une reponse en streaming avec gestion des erreurs"""
        if not settings.groq_api_key:
            yield "erreur : la cle api groq n'est pas configuree dans le fichier .env"
            return

        try:
            stream = await self._create_stream(prompt, system_message)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"erreur critique service llm : {e}")
            yield f"\n\n[erreur] : {e}"

llm_service = LLMService()
