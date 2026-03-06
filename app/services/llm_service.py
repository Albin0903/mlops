import time
from groq import AsyncGroq
from google import genai
from google.genai import types
from loguru import logger
from langfuse import get_client
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

# regle : resilience, streaming et observabilite pour l'excellence mlops

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
        "tu es un assistant intelligent et logique. "
        "base ta reponse sur le document fourni. "
        "tu peux raisonner, deduire et faire des inferences logiques a partir du contexte. "
        "si le document ne contient aucune information pertinente, repond 'information non disponible dans le document'. "
        "reponse concise et argumentee. "
        "langue du document : {language}."
    ),
}

# cout par token par modele (prix publics)
TOKEN_COST = {
    "groq": {
        "input": 0.59 / 1_000_000,   # $0.59 par million de tokens groq
        "output": 0.79 / 1_000_000,
    },
    "gemini": {
        "input": 0.0 / 1_000_000,    # gemini 3.1 flash lite preview : gratuit
        "output": 0.0 / 1_000_000,
    },
}

# configuration des modeles par provider
PROVIDER_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-3.1-flash-lite-preview",
}


class LLMService:
    def __init__(self):
        """initialisation des clients llm (groq + gemini)"""
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None
        self.gemini_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    def get_system_prompt(self, mode: str, language: str) -> str:
        """retourne le prompt systeme optimise selon le mode"""
        return SYSTEM_PROMPTS[mode].format(language=language)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _create_groq_stream(self, prompt: str, system_message: str):
        """cree le flux groq (retryable car ne yield pas)"""
        return await self.groq_client.chat.completions.create(
            model=PROVIDER_MODELS["groq"],
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
            top_p=1,
            stream=True,
        )

    async def _stream_groq(self, prompt: str, system_message: str):
        """generateur de streaming pour groq"""
        input_tokens = 0
        output_tokens = 0
        stream = await self._create_groq_stream(prompt, system_message)
        async for chunk in stream:
            if hasattr(chunk, "x_groq") and chunk.x_groq and hasattr(chunk.x_groq, "usage"):
                usage = chunk.x_groq.usage
                input_tokens = getattr(usage, "prompt_tokens", 0)
                output_tokens = getattr(usage, "completion_tokens", 0)

            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content, input_tokens, output_tokens

    async def _stream_gemini(self, prompt: str, system_message: str):
        """generateur de streaming pour gemini avec google search et thinking"""
        full_prompt = f"{system_message}\n\n{prompt}"

        # outils : google search pour grounding des reponses
        tools = [
            #types.Tool(google_search=types.GoogleSearch()), # google search non disponible en free tier
        ]

        # configuration avancee : thinking mode pour un raisonnement approfondi
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
            tools=tools,
        )

        response = self.gemini_client.models.generate_content_stream(
            model=PROVIDER_MODELS["gemini"],
            contents=full_prompt,
            config=config,
        )
        for chunk in response:
            if chunk.text:
                input_tokens = getattr(chunk.usage_metadata, "prompt_token_count", 0) if chunk.usage_metadata else 0
                output_tokens = getattr(chunk.usage_metadata, "candidates_token_count", 0) if chunk.usage_metadata else 0
                yield chunk.text, input_tokens, output_tokens

    async def get_streaming_response(self, prompt: str, system_message: str, mode: str = "doc", provider: str = "groq"):
        """genere une reponse en streaming avec observabilite langfuse (multi-provider)"""

        # verification de la cle api
        if provider == "groq" and not settings.groq_api_key:
            yield "erreur : la cle api groq n'est pas configuree dans le fichier .env"
            return
        if provider == "gemini" and not settings.gemini_api_key:
            yield "erreur : la cle api gemini n'est pas configuree dans le fichier .env"
            return

        start_time = time.perf_counter()
        full_response = []
        input_tokens = 0
        output_tokens = 0
        model = PROVIDER_MODELS.get(provider, "unknown")

        try:
            # selection du stream selon le provider
            if provider == "gemini":
                stream = self._stream_gemini(prompt, system_message)
            else:
                stream = self._stream_groq(prompt, system_message)

            async for content, in_tok, out_tok in stream:
                full_response.append(content)
                input_tokens = in_tok or input_tokens
                output_tokens = out_tok or output_tokens
                yield content

        except Exception as e:
            logger.error(f"erreur critique service llm ({provider}) : {e}")
            yield f"\n\n[erreur] : {e}"
            return

        # calcul des metriques finales
        latency = time.perf_counter() - start_time
        provider_costs = TOKEN_COST.get(provider, TOKEN_COST["groq"])
        cost = (input_tokens * provider_costs["input"]) + (output_tokens * provider_costs["output"])

        logger.info(
            f"llm call completed | provider={provider} | model={model} | mode={mode} | "
            f"latency={latency:.2f}s | tokens_in={input_tokens} | "
            f"tokens_out={output_tokens} | cost=${cost:.6f}"
        )

        # enregistrement dans langfuse si configure
        if settings.langfuse_enabled:
            try:
                langfuse = get_client()
                with langfuse.start_as_current_observation(
                    name=f"llm-{mode}-{provider}",
                    as_type="generation",
                    model=model,
                ) as generation:
                    generation.update(
                        input={"prompt": prompt, "system_message": system_message},
                        output="".join(full_response),
                        usage_details={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        },
                        metadata={
                            "provider": provider,
                            "mode": mode,
                            "latency_seconds": round(latency, 3),
                            "estimated_cost_usd": round(cost, 6),
                            "model": model,
                        },
                    )
            except Exception as e:
                logger.warning(f"langfuse logging failed (non-blocking) : {e}")


llm_service = LLMService()
