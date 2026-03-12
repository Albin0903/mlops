# Scalable & secure LLM code analyzer

[![CI Pipeline](https://github.com/Albin0903/mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/Albin0903/mlops/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-multi--stage-2496ED.svg)](Dockerfile)

API d'analyse de code par LLM, avec un vrai focus infra : conteneurisation, CI/CD GitOps, monitoring, resilience et maitrise des couts. Projet MLOps complet, pas juste un wrapper autour d'un modele.

## Tech Stack

| Domaine | Outils |
|---|---|
| **API** | Python 3.13, FastAPI (100% async), streaming SSE |
| **LLM** | Multi-provider : Groq (Llama 8b/70b, GPT-OSS 120B) + Google Gemini (Flash Lite) |
| **Observabilite** | Langfuse (tracing, tokens, cout), Prometheus + Grafana (dashboards as code) |
| **Infra** | Terraform (VPC/IAM/EKS), Kubernetes (minikube), Docker multi-stage non-root |
| **CI/CD** | GitHub Actions (Ruff, Pytest, Trivy, GHCR) + ArgoCD (GitOps auto-sync) |
| **Resilience** | Tenacity (retry backoff exponentiel), multi-provider fallback |
| **Tests** | Pytest (99% couverture) + Locust (load testing) |
| **Securite** | Trivy, pre-commit, detect-secrets, Docker non-root |

## Architecture

```text
mlops/
├── app/                          # api fastapi
│   ├── api/routes/               # endpoints (analysis, health)
│   ├── core/                     # config centralisee (secrets, env)
│   ├── schemas/                  # modeles pydantic
│   └── services/                 # logique metier (llm_service)
├── gitops/                       # manifests k8s (argocd)
│   ├── base/                     # deployment, service, ingress
│   └── overlays/minikube/        # overlay env local
├── k8s/monitoring/               # prometheus + grafana (dashboards as code)
├── terraform/modules/            # iac (vpc, iam, cluster)
├── tests/                        # pytest + locustfile
├── scripts/                      # dagger ci, manage_infra, test_streaming
├── .github/workflows/ci.yml      # pipeline ci 4 jobs
└── Dockerfile                    # multi-stage, non-root, healthcheck
```

## Quick Start

```powershell
# 1. prerequis : docker desktop, minikube, kubectl

# 2. lancer le cluster
minikube start --driver=docker
minikube addons enable ingress

# 3. build + deploy
docker build -t mlops-api:latest .
minikube image load mlops-api:latest
kubectl apply -f gitops/base/ -n mlops
kubectl apply -f k8s/monitoring/ -n mlops

# 4. port-forward (dans des terminaux separes)
kubectl port-forward svc/mlops-api -n mlops 8000:80
kubectl port-forward svc/grafana-service -n mlops 3000:3000

# 5. tester
curl http://localhost:8000/health/
```

## Utilisation

**Generer la doc d'une fonction :**
```bash
curl -N -X POST "http://localhost:8000/analyze/" \
  -H "Content-Type: application/json" \
  -d '{"content": "def fib(n): return n if n<=1 else fib(n-1)+fib(n-2)", "language": "python", "mode": "doc"}'
```

**Poser une question sur un document :**
```bash
curl -N -X POST "http://localhost:8000/analyze/" \
  -H "Content-Type: application/json" \
  -d '{"content": "Le projet utilise Terraform et K8s.", "language": "text", "mode": "question", "question": "Quels outils IaC ?"}'
```

**Choisir un modele specifique :**
```bash
# providers : groq (defaut), gemini, instant (llama 8b), medium (llama 70b), gpt (120b)
curl -N -X POST "http://localhost:8000/analyze/" \
  -H "Content-Type: application/json" \
  -d '{"content": "class Db: pass", "language": "python", "mode": "doc", "provider": "gemini"}'
```

## Monitoring

- **Grafana** : `http://localhost:3000` (admin / admin)
- **Prometheus** : collecte automatique via `prometheus-fastapi-instrumentator`
- **Metriques custom** : `llm_requests_total`, `llm_tokens_total`, `llm_latency_seconds`, `llm_errors_total`

## Tests de charge

```powershell
# installer locust
pip install -r requirements-dev.txt

# lancer le benchmark (1 min, 50% de la charge max des quotas)
locust -f tests/locustfile.py --host http://localhost:8000 --users 5 --spawn-rate 1 --run-time 1m --headless
```

## CI/CD

Pipeline GitHub Actions en 4 jobs paralleles :
1. **Lint** : `ruff check` + `ruff format --check`
2. **Tests** : `pytest` avec couverture (seuil 70%)
3. **Security** : scan Trivy (CRITICAL + HIGH)
4. **Build & Push** : image Docker vers GHCR (main uniquement)

Deploiement continu via **ArgoCD** (auto-sync depuis `gitops/base/`).

## Continuous Integration (Dagger)

Le projet utilise **Dagger** pour exécuter le pipeline de CI de manière programmable.

### Exécution locale
```powershell
python scripts/dagger_ci.py
```

### Exécution avec Dagger Cloud
Le script `scripts/dagger_ci.py` charge automatiquement le `DAGGER_CLOUD_TOKEN` depuis votre fichier `.env`. Pour bénéficier de l'observabilité complète sur l'interface **[Dagger Cloud](https://dagger.cloud)** :

```powershell
# Assurez-vous d'avoir le CLI Dagger installé
dagger run python scripts/dagger_ci.py
```

Vous pouvez également lancer manuellement avec le token en variable d'environnement :
```powershell
$env:DAGGER_CLOUD_TOKEN="votre_token"; dagger run python scripts/dagger_ci.py
```

## Configuration

Creer un fichier `.env` a la racine :
```dotenv
groq_api_key=gsk_xxx
gemini_api_key=xxx
langfuse_public_key=pk-lf-xxx
langfuse_secret_key=sk-lf-xxx
```

## Dev Setup

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload
```

---

[Suivi du projet](PROGRESS.md) | [Backlog](TODO.md) | [Standards](docs/engineering_standards.md) | [GitOps](docs/argocd_gitops.md)
