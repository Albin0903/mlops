# Plan de migration API-only (contrat)

Ce document est le contrat de migration pour la refonte modulaire API-first.
Il fige le perimetre produit, l'architecture cible et la cartographie old-to-new.

## Phase 0 - Baseline produit (figee)

Matrice des fonctionnalites cibles du coeur produit V1:

| Domaine | Etat actuel | Cible API-only | Statut |
|---|---|---|---|
| Analyze streaming | `POST /analyze/` (SSE) avec use case applicatif | Conserver dans coeur produit | Keep |
| Health | `GET /health/` avec use case `HealthCheckUseCase` | Conserver dans coeur produit | Keep |
| Providers | Groq, Gemini, Ollama via registry/factory | Conserver dans coeur produit | Keep |
| Observabilite | Prometheus + Langfuse + dashboards Grafana | Conserver dans coeur produit | Keep |
| CI qualite | `make ci-local` + GitHub Actions (lint/tests/cov/security) | Conserver dans coeur produit | Keep |
| Container runtime | Dockerfile multi-stage + deployment K8s | Conserver dans coeur produit | Keep |

## Phase 0 - Scope contractuel (fige)

Inclus dans le coeur produit:
- API FastAPI (`analyze`, `health`), schemas et validation.
- Couche application (use cases + ports).
- Couche domain (objets metier analyse/sante).
- Couche infrastructure (adapters providers, observabilite, config runtime).
- Tests API-first, outillage qualite, containerisation.

Exclus du coeur produit (legacy/lab ou repo dedie):
- Solveurs jeux (`scripts/pedantix`, `scripts/tusmo`).
- Bot Selenium et automatisations non API-first.
- Benchmarks agents hors flux produit API.
- Artefacts de test ad hoc hors pipeline standard.

Regle contractuelle:
- Aucun module exclu ne doit etre requis pour executer l'API coeur produit.

## Phase 1 - Architecture cible (modular monolith)

Couches officielles:
- Presentation: `app/api`, `app/schemas`.
- Application: `app/application` (use cases + ports).
- Domain: `app/domain`.
- Infrastructure: `app/infrastructure`, `app/services` (adapters techniques).

Regles de dependance:
- `presentation -> application -> domain`
- `infrastructure -> application (ports) + domain`
- `application` ne depend pas de `infrastructure` concrete.
- La composition des dependances est centralisee dans `app/infrastructure/composition.py`.

## Phase 1 - Cartographie old-to-new

| Module actuel | Module cible | Cible de couche | Statut migration |
|---|---|---|---|
| `app/api/routes/analysis.py` | `app/api/routes/analysis.py` + use case | Presentation | Migre |
| `app/api/routes/health.py` | `app/api/routes/health.py` + use case | Presentation | Migre |
| `app/schemas/analysis.py` | `app/schemas/analysis.py` | Presentation | Migre |
| `app/services/llm_service.py` | Adapter technique derriere port `LLMGateway` | Infrastructure | Migre |
| `app/services/llm/factory.py` | Registry providers injectee via composition root (`LLMProviderRegistry`) | Infrastructure | Migre |
| `app/services/prompt_manager.py` | `BuildPromptUseCase` + contrat `PromptSpec` | Application/Infra | Migre |
| `app/services/provider_registry.py` | Resolution provider (adapter infra) | Infrastructure | Migre |
| `app/services/observability.py` | Facade observabilite decouplee (via port `ObservabilityGateway`) | Infrastructure | Migre |
| `app/services/llm/groq.py` | Adapter provider Groq | Infrastructure | Migre |
| `app/services/llm/gemini.py` | Adapter provider Gemini | Infrastructure | Migre |
| `app/services/llm/ollama.py` | Adapter provider Ollama | Infrastructure | Migre |
| `app/application/use_cases/resolve_provider.py` | Use case de resolution provider (branche dans `AnalyzeStreamUseCase`) | Application | Migre |
| `app/application/use_cases/execute_agent_call.py` | Use case appels agent non-streaming (provider resolu) | Application | Migre |
| `app/domain/usage.py` | Contrat tokens in/out (`TokenUsage`) | Domain | Migre |
| `scripts/pedantix/**` | `legacy/` ou repo dedie | Hors coeur | A decommissionner |
| `scripts/tusmo/**` | `legacy/` ou repo dedie | Hors coeur | A decommissionner |
| `scripts/test_streaming.py` | Test integration officiel | Hors coeur (si ad hoc) | A trier |

## Livrables clos par ce document

- Baseline produit API-only figee.
- Scope contractuel include/exclude valide.
- Architecture cible avec regles strictes de dependance.
- Cartographie old-to-new explicite pour migration parallele.

## Suivi d'execution des phases (maj 2026-04-03)

- [x] Phase 0 - Baseline produit (analyze, health, providers, observabilite, CI, container).
- [x] Phase 0 - Scope contractuel (coeur API-first vs legacy hors coeur).
- [x] Phase 1 - Architecture cible en couches avec regles strictes.
- [x] Phase 1 - Cartographie old-to-new pour migration parallele.
- [x] Phase 2 - Classes metier et contrats stabilises (provider, prompt, usage, health, ports).
- [x] Phase 2 - Use cases applicatifs centralises (stream analyze, prompt building, provider resolution, health).
- [x] Phase 3 - Adapters providers harmonises sur socle commun.
- [x] Phase 3 - Composition API avec injection explicite, sans singleton metier global.
- [x] Phase 3 - Observabilite decouplee via composants dedies.
- [x] Phase 4 (partiel) - Defaut provider local passe a `gemma4b` + aliases enrichis pour appel des modeles.
- [x] Phase 4 (partiel) - Hygiene outillage/debug via dossier `tmp/` et ignore git des artefacts locaux.
- [x] Phase 4 - Tooling simplifie complet (rationalisation finale des dependances runtime/dev).
- [x] Phase 4 - Qualite automatisee complete (parite locale/CI strictement bloquante sur tous les gates).
- [ ] Phase 5 (en cours) - Pyramide de tests structuree (cibles unit/contract/integration/e2e + scenario E2E minimal).
- [ ] Phase 5 - Refonte de la pyramide de tests (unitaires, contrats adapters, integration streaming, E2E minimal).
- [ ] Phase 5 - Documentation et consignes agents harmonisees avec l'etat reel du code.
- [ ] Phase 5 - Decommission legacy hors coeur API-first (solveurs/bots/bench ad hoc).
- [ ] Phase 6 - Cutover final (entree principale, nettoyage ancien chemin, stabilisation release).

## Suite immediate (ordre de travail)

1. Executer la refonte tests par couche/contrat/integration/E2E minimal (Phase 5).
2. Harmoniser la doc et les directives agents sur le flux API-only courant (Phase 5).
3. Decommissionner les modules legacy non API-first (Phase 5).
4. Basculer sur le cutover final (Phase 6): entree principale, nettoyage ancien chemin, stabilisation release.
