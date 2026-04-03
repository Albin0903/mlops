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
- `provider` (valeurs supportees par le registry)

## Providers supportes

- Groq: `groq`, `instant`, `medium`, `gpt`
- Gemini: `gemini`
- Ollama local: `ollama`, `ollama-medium`, `ollama-small`, `ollama-mini`, `ollama-llama3`

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
