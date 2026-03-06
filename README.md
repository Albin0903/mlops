# Scalable & secure LLM code analyzer

[![CI Pipeline](https://github.com/Albin0903/mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/Albin0903/mlops/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-multi--stage-2496ED.svg)](Dockerfile)

## Objectif
Concevoir, déployer et monitorer une API d'analyse de code alimentée par des LLMs. Ce projet met l'accent sur l'**excellence de l'infrastructure** (haute disponibilité, sécurité, maitrise des coûts, CI/CD moderne) plutôt que sur la seule performance du modèle d'IA.

## Pile technique
- **Langages :** Python 3.13, FastAPI (100% asynchrone)
- **LLM :** Groq API (Llama 3.3 70B) avec streaming temps réel
- **Infrastructure :** Terraform (modules VPC/IAM), Kubernetes (minikube/EKS)
- **Résilience :** Tenacity (retry avec backoff exponentiel)
- **CI/CD :** GitHub Actions, ArgoCD (GitOps)
- **Observabilité :** Prometheus, Grafana, Langfuse
- **Sécurité :** Trivy, pre-commit, detect-secrets, Docker non-root

## Architecture du projet
```text
mlops/
├── app/                          # code source de l'api (fastapi)
│   ├── api/routes/               # endpoints (analysis, health)
│   ├── core/                     # configuration centralisee (secrets, env)
│   ├── schemas/                  # contrats de donnees (pydantic)
│   └── services/                 # logique metier (llm_service)
├── k8s/                          # manifestes kubernetes
├── terraform/modules/            # infrastructure as code (vpc, iam, cluster)
├── scripts/                      # automatisation (manage_infra, test_streaming)
├── Dockerfile                    # multi-stage build, utilisateur non-root
├── requirements.txt              # dependances production
└── PROGRESS.md                   # suivi du projet (24 semaines)
```

## Fonctionnalités
- **Génération de documentation :** Soumettez du code source et recevez une documentation Markdown structurée en streaming.
- **Questions sur documents :** Posez des questions précises sur un fichier technique et obtenez une réponse factuelle.
- **Streaming temps réel :** Les réponses du LLM sont envoyées chunk par chunk via Server-Sent Events.
- **Gestion des coûts :** Prompts systèmes optimisés pour réduire la consommation de tokens (FinOps).
- **Résilience :** Retry automatique avec backoff exponentiel en cas d'erreur réseau.
- **Sécurité :** Image Docker non-root, secrets injectés via `.env`, scan pre-commit.

---

## Guide utilisateur (User)
Cette section décrit comment interagir avec l'API une fois déployée.

### Accès à l'API
L'API est accessible via Swagger UI (documentation interactive) :
- **URL locale :** `http://localhost:8000/docs` (si le port-forward est actif)
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
aws_id_key=votre_cle_aws
aws_secret_key=votre_secret_aws
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
Le projet utilise minikube pour le développement sans frais.
- **Démarrer le cluster :** `minikube start --driver=docker`
- **Activer l'Ingress :** `minikube addons enable ingress`
- **Déployer les manifestes :** `kubectl apply -f k8s/`
- **Arrêter le cluster :** `minikube stop`

### Automatisation (Scripts Python)
```powershell
# deployer l'infrastructure terraform
python scripts/manage_infra.py up --yes

# deployer les manifestes kubernetes
python scripts/manage_infra.py deploy

# detruire l'infrastructure (finops)
python scripts/manage_infra.py down --yes
```

---

> Note : Ce projet est actuellement en phase de développement actif. [Suivre l'avancement ici](PROGRESS.md).
>
> Les standards d'ingénierie appliqués sont documentés dans le [guide des standards](docs/engineering_standards.md).
