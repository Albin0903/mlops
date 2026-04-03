# LLM Code Analyzer (MLOps/LLMOps)

CI Pipeline: https://github.com/Albin0903/mlops/actions/workflows/ci.yml
Python: 3.13
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
- Ruff (`check` + `format --check`)
- Pytest complet
- Couverture minimale enforcee a 90%

## Providers supportes

- Groq: `groq`, `instant`, `medium`, `gpt`
- Gemini: `gemini`
- Ollama local: `ollama`, `ollama-medium`, `ollama-small`, `ollama-mini`, `ollama-llama3`

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
