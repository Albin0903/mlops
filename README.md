# LLM code analyzer (MLOps/LLMOps)

CI Pipeline: https://github.com/Albin0903/mlops/actions/workflows/ci.yml
Python: 3.13
Docker: multi-stage

Plateforme de demonstration MLOps appliquee aux modeles de langage (LLMOps).

## Sommaire de la documentation

Le projet est divise en modules de documentation :

1.  [Fonctionnalites API](docs/features.md) : Streaming SSE, multi-provider (Groq/Gemini), schemas Pydantic.
2.  [Infrastructure et GitOps](docs/infrastructure.md) : Role de Minikube, Terraform, ArgoCD et Kubernetes.
3.  [Observabilite](docs/observability.md) : Prometheus, Grafana, tracing via Langfuse.
4.  [Demonstrations](docs/demos.md) : Solveurs Tusmo et Pedantix (validation du systeme).

## Demarrage rapide

```powershell
# 1. Preparer l'environnement
make dev

# 2. Lancer l'infrastructure locale (Minikube requis)
make build-local
make deploy

# 3. Verifier le status
curl http://localhost:8000/health/
```

## Architecture

```text
mlops/
├── app/          # Core API FastAPI (Async, Metriques, Services)
├── gitops/       # Manifests GitOps (ArgoCD)
├── k8s/          # Configurations & Dashboards (Prometheus/Grafana)
├── terraform/    # IaC pour deploiement Cloud
├── docs/         # Documentation modulaire
└── scripts/      # Solveurs & Tests (Dagger CI, Pédantix)
```

## Vision du projet
Ce projet demontre la mise en place d'une infrastructure pour des services s'appuyant sur l'IA generative.

---
[Suivi du projet](PROGRESS.md) | [Backlog](TODO.md)
