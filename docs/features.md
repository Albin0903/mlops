# Fonctionnalites API

Ce document detaille les fonctionnalites de l'API LLM code analyzer.

## Streaming SSE (Server-Sent Events)

L'API utilise FastAPI pour envoyer des reponses LLM en temps reel.
- Endpoint : `POST /analyze/`
- Activation automatique via le parametre `-N` ou `stream=True`.
- Reduction du temps d'attente pour le premier token.

## Multi-provider et fallback

L'architecture supporte plusieurs fournisseurs pour garantir la resilience.
- Groq : Llama 3.1 8b, Llama 3.3 70b, GPT-OSS 120b.
- Google Gemini : Gemini 1.5 Flash-Lite avec Thinking Mode.
- Fallback : Basculement dynamique en cas d'erreur (via retry).

## Modes d'analyse

1. Documentation (`doc`) : Genere une documentation Markdown structuree.
2. Question Answering (`question`) : Repond a des questions basees sur un document.

## Resilience et validation

- Tenacity : Retry avec backoff exponentiel.
- Pydantic V2 : Validation des schemas.
- System Prompts : Prompts optimises pour reduire la consommation de tokens.
