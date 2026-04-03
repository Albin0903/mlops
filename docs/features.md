# Fonctionnalites API

Ce document detaille les fonctionnalites exposees par l'API FastAPI.

## Endpoint principal

- Endpoint: `POST /analyze/`
- Type de reponse: `text/event-stream` (SSE)
- Cas d'usage: generation de documentation technique et reponse a une question sur un contenu donne

## Contrat de requete

Le schema `AnalysisRequest` valide:
- `content` (obligatoire)
- `language` (defaut: `python`)
- `mode` (`doc` ou `question`)
- `question` (optionnel, utile en mode `question`)
- `provider` (defaut: `gemma4b`, valeurs supportees par le registry)

## Providers supportes

- Groq: `groq`, `instant`, `medium`, `gpt`
- Gemini: `gemini`
- Ollama local (defaut): `ollama`, `gemma4b`, `gemma4-e4b`, `gemma4-e2b`, `gemma4-26b`, `ollama-medium`, `ollama-small`, `ollama-mini`, `ollama-llama3`
- Aliases de confort: `qwen9b`, `qwen2b`, `qwen0.8b`, `local`, `default`

## Modes d'analyse

1. `doc`: genere une documentation Markdown structuree.
2. `question`: repond de facon concise a partir du contenu fourni.

## Resilience et robustesse

- Retry Groq en streaming via Tenacity (backoff exponentiel).
- Gestion des erreurs provider avec message technique controle.
- Normalisation des comportements providers (streaming + appels agent non-streaming).

## Validation et prompts

- Validation stricte Pydantic pour eviter les payloads invalides.
- Prompts systeme centralises (`doc` et `question`) pour garder une sortie stable.
