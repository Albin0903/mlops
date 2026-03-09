# Scalable & secure LLM code analyzer

[![CI Pipeline](https://github.com/Albin0903/mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/Albin0903/mlops/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-multi--stage-2496ED.svg)](Dockerfile)

## Objectif
Une API d'analyse de code qui s'appuie sur des LLMs, avec un vrai focus sur l'infra : haute dispo, securite, maitrise des couts et CI/CD moderne. L'idee c'est de montrer un projet MLOps complet, pas juste un wrapper autour d'un modele.

## Pile technique
- **Langages :** Python 3.13, FastAPI (100% asynchrone)
- **LLM :** Multi-provider — Groq (GPT-OSS 120B) + Google Gemini (3.1 Flash Lite) avec streaming temps réel
- **Observabilité LLM :** Langfuse (tracing, tokens, coût par requête)
- **Infrastructure :** Terraform (modules VPC/IAM), Kubernetes (minikube/EKS)
- **Résilience :** Tenacity (retry avec backoff exponentiel)
- **CI/CD :** GitHub Actions (Ruff, Pytest, Trivy, GHCR), ArgoCD (GitOps)
- **Tests :** Pytest + pytest-cov (99% de couverture)
- **Sécurité :** Trivy, pre-commit, detect-secrets, Docker non-root

## Architecture du projet
```text
mlops/
├── app/                          # code source fastapi
│   ├── api/routes/               # endpoints (analysis, health)
│   ├── core/                     # config centralisee (secrets, env)
│   ├── schemas/                  # modeles pydantic
│   └── services/                 # logique metier (llm_service)
├── gitops/                       # manifests kubernetes (gitops)
│   ├── base/                     # deployment, service, ingress
│   └── overlays/minikube/        # overlay pour l'env local
├── argocd/applications/          # declaration de l'app argocd
├── k8s/                          # manifests kubernetes (demo)
├── terraform/modules/            # iac (vpc, iam, cluster)
├── scripts/                      # automatisation python
├── docs/                         # documentation technique
├── Dockerfile                    # multi-stage, non-root
└── PROGRESS.md                   # suivi du projet
```

## Fonctionnalites
- **Multi-provider :** Groq et Gemini selectionnables via le parametre `provider`.
- **Generation de doc :** soumet du code, recois une doc Markdown structuree en streaming.
- **Q&A sur documents :** pose une question sur un fichier technique, obtiens une reponse argumentee.
- **Streaming SSE :** les reponses arrivent chunk par chunk en temps reel.
- **Tracing LLM :** chaque appel est trace dans Langfuse (tokens, cout, latence).
- **FinOps :** prompts optimises, cout calcule par requete.
- **Resilience :** retry avec backoff exponentiel sur erreurs reseau.
- **Securite :** image Docker non-root, secrets via `.env`, scan pre-commit.
- **CI/CD :** GitHub Actions (Ruff, Pytest, Trivy, GHCR) + ArgoCD pour le deploiement GitOps.

---

## Guide utilisateur (User)
Cette section décrit comment interagir avec l'API une fois déployée.

### Accès à l'API
L'API est accessible via Swagger UI (documentation interactive) :
- **URL locale :** `http://localhost:8000/docs` (Activer le tunnel : `kubectl port-forward svc/mlops-api -n mlops 8000:80`)
- **URL Kubernetes :** `http://mlops-api.local/docs` (via l'Ingress)

### Endpoints disponibles

| Méthode | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Vérification que l'API est opérationnelle |
| `GET` | `/health/` | Statut de santé et version |
| `POST` | `/analyze/` | Analyse de code ou question sur document (streaming) |

### Exemples d'utilisation

**Générer la documentation d'une fonction :**
```bash
curl -N -X POST "http://localhost:8000/analyze/" \
  -H "Content-Type: application/json" \
  -d '{"content": "def fibonacci(n: int) -> int:\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)", "language": "python", "mode": "doc"}'
```

**Poser une question sur un document :**
```bash
curl -N -X POST "http://localhost:8000/analyze/" \
  -H "Content-Type: application/json" \
  -d '{"content": "Le projet utilise Terraform et minikube.", "language": "text", "mode": "question", "question": "Quels outils sont utilisés ?"}'
```

**Vérification de santé :**
```bash
curl -X GET "http://localhost:8000/health/"
```

---

## Guide développeur (Dev)
Cette section détaille les commandes nécessaires pour maintenir et faire évoluer l'infrastructure.

### Environnement local
```powershell
# activer l'environnement virtuel
.venv\Scripts\Activate.ps1

# installer les dependances
pip install -r requirements.txt
pip install -r requirements-dev.txt

# configurer la securite
pre-commit install

# lancer l'api en mode developpement
uvicorn app.main:app --reload
```

### Configuration des secrets
Créer un fichier `.env` à la racine du projet :
```dotenv
groq_api_key=gsk_votre_cle_ici
gemini_api_key=votre_cle_gemini
aws_id_key=votre_cle_aws
aws_secret_key=votre_secret_aws
langfuse_public_key=pk-lf-xxx
langfuse_secret_key=sk-lf-xxx
```

### Validation du streaming
Un script de test asynchrone est disponible pour valider que le streaming fonctionne correctement :
```powershell
python scripts/test_streaming.py
```
Si le nombre de chunks reçus est supérieur à 1, le streaming est validé.

### Infrastructure (Terraform)
Toutes les commandes doivent être lancées depuis le dossier `terraform/`.
- **Initialiser :** `terraform init`
- **Vérifier les changements :** `terraform plan`
- **Déployer le réseau/IAM :** `terraform apply`

### Kubernetes (minikube)
Le projet utilise minikube pour le dev local (zero frais).
- **Demarrer le cluster :** `minikube start --driver=docker`
- **Activer l'Ingress :** `minikube addons enable ingress`
- **Deployer les manifests :** `kubectl apply -f k8s/`
- **Arreter le cluster :** `minikube stop`

### CI/CD Moderne (Dagger)
Le projet utilise **Dagger** pour permettre l'exécution du pipeline de CI localement, exactement comme sur GitHub Actions.
```powershell
# installer dagger (via pip)
pip install -r requirements-dev.txt

# lancer la CI locale (lint + tests + build)
python scripts/dagger_ci.py
```
Cela garantit que "si ça passe sur mon PC, ça passera sur la CI".

### Deploiement GitOps (ArgoCD)
Le deploiement continu est gere par ArgoCD. Les manifests Kubernetes vivent dans `gitops/` et ArgoCD synchronise automatiquement le cluster avec ce qui est declare dans Git.

```powershell
# installer argocd sur le cluster (une seule fois)
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# declarer l'application
kubectl apply -f argocd/applications/mlops.yaml

# verifier le statut
kubectl get applications -n argocd

# acceder a l'interface web
kubectl port-forward svc/argocd-server -n argocd 8080:443
# puis ouvrir https://localhost:8080
```

Plus de details dans [docs/argocd_gitops.md](docs/argocd_gitops.md).

### Monitoring (Prometheus & Grafana)
Le monitoring est assuré par Prometheus pour la collecte des métriques et Grafana pour la visualisation.

```powershell
# deployer la stack de monitoring
kubectl apply -f k8s/monitoring/prometheus-grafana.yaml

# acceder au dashboard grafana
kubectl port-forward svc/grafana-service -n mlops 3000:3000
# ouvrir http://localhost:3000 (admin / admin)
```

### Automatisation (Scripts Python)
```powershell
# deployer l'infrastructure terraform
python scripts/manage_infra.py up --yes

# deployer les manifests kubernetes
python scripts/manage_infra.py deploy

# detruire l'infrastructure (finops)
python scripts/manage_infra.py down --yes
```

---

> Ce projet est en developpement actif. [Suivre l'avancement](PROGRESS.md) | [Standards du projet](docs/engineering_standards.md)
