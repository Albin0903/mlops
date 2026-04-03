# LLM Code Analyzer (MLOps/LLMOps)

CI Pipeline: https://github.com/Albin0903/mlops/actions/workflows/ci.yml
Python: 3.14
Docker: multi-stage

Plateforme API-first pour l'analyse de code en streaming SSE avec providers LLM multiples et observabilite integree.

## Sommaire de la documentation

1. [Fonctionnalites API](docs/features.md)
2. [Infrastructure et GitOps](docs/infrastructure.md)
3. [Observabilite](docs/observability.md)
4. [Demonstrations](docs/demos.md)
5. [Plan de migration API-only](docs/api_only_migration_plan.md)
6. [Workflow de developpement](docs/dev_workflow.md)

## Demarrage rapide (local)

```bash
# 1) Installer dependances + hooks
make install

# 1-bis) Optionnel: installer les outils hors gate core (dagger, locust, selenium)
make install-optional

# 2) Lancer l'API
make dev

# 3) Verifier la sante
curl http://localhost:8000/health/

# 4) Test streaming (SSE)
curl -N -X POST http://localhost:8000/analyze/ \
	-H "Content-Type: application/json" \
	-d '{"content":"def add(a,b): return a+b","language":"python","mode":"doc","provider":"groq"}'
```

## Qualite locale (parite CI)

```bash
make ci-local
```

Gate principal:
- Prepush quality gates (ruff, format, yaml, secrets, terraform, manifests K8s)
- Pytest complet
- Couverture minimale enforcee a 90%

Execution par couche (Phase 5):

```bash
make test-unit
make test-contract
make test-integration
make test-e2e
make test-pyramid
```

## Providers supportes

- Groq: `groq`, `instant`, `medium`, `gpt`
- Gemini: `gemini`
- Ollama local (defaut: `gemma4b`): `ollama`, `gemma4b`, `gemma4-e4b`, `gemma4-e2b`, `gemma4-26b`, `ollama-medium`, `ollama-small`, `ollama-mini`, `ollama-llama3`
- Aliases pratiques: `qwen9b`, `qwen2b`, `qwen0.8b`, `local`, `default`

## Architecture API-only

```text
mlops/
├── app/
│   ├── api/             # Routes FastAPI
│   ├── application/     # Use cases + ports
│   ├── domain/          # Modeles metier
│   ├── infrastructure/  # Adapters + composition
│   ├── schemas/         # Validation Pydantic
│   └── services/        # Providers LLM + observabilite
├── tests/               # Unitaires + integration
├── gitops/              # Manifests GitOps
├── k8s/                 # Monitoring et dashboards
├── terraform/           # IaC (modules)
└── docs/                # Documentation modulaire
```

## Deploiement local Kubernetes

```bash
make build-local
make deploy
```

## One-command demo (build + deploy + port-forward)

```bash
make demo
```

Le script lance la stack locale et ouvre les endpoints API/Grafana/Prometheus/Loki.

---
[Suivi du projet](PROGRESS.md) | [Backlog](TODO.md)
