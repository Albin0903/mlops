# Scalable & secure LLM code analyzer

## Objectif
Concevoir, déployer et monitorer une API d'analyse de code alimentée par des LLMs. Ce projet met l'accent sur l'**excellence de l'infrastructure** (haute disponibilité, sécurité, maitrise des coûts, CI/CD moderne) plutôt que sur la seule performance du modèle d'IA.

## Pile technique
- **Langages :** Python, FastAPI (Asynchrone)
- **Infrastructure :** Terraform, Kubernetes (minikube/EKS)
- **CI/CD :** GitHub Actions, ArgoCD (GitOps)
- **Observabilité :** Prometheus, Grafana, Langfuse
- **Sécurité :** Trivy, pre-commit, detect-secrets

## Fonctionnalités
- **Analyse de code :** Interface API pour soumettre des extraits de code et recevoir des suggestions d'optimisation.
- **Gestion des coûts :** Suivi précis de l'utilisation des tokens et estimation du coût par requête.
- **Résilience :** Implémentation de mécanismes de retry avec backoff exponentiel pour les appels LLM.
- **GitOps :** Synchronisation automatique de l'état du cluster avec le dépôt Git.

---

## Guide utilisateur (User)
Cette section décrit comment interagir avec l'API une fois déployée.

### Accès à l'API
L'API est accessible via Swagger UI (documentation interactive) :
- **URL locale :** `http://localhost:8000/docs` (si le port-forward est actif)
- **URL Kubernetes :** `http://mlops-api.local/docs` (via l'Ingress)

### Commandes principales
- **Soumission d'analyse :**
  ```bash
  curl -X POST "http://localhost:8000/analyze" -H "Content-Type: application/json" -d '{"code": "print('hello')", "language": "python"}'
  ```
- **Vérification de santé :**
  ```bash
  curl -X GET "http://localhost:8000/health"
  ```

---

## Guide développeur (Dev)
Cette section détaille les commandes nécessaires pour maintenir et faire évoluer l'infrastructure.

### Environnement local
- **Activer l'environnement :** `.venv\Scripts\Activate.ps1`
- **Installer les dépendances :** `pip install -r requirements.txt`
- **Configurer la sécurité :** `pre-commit install`

### Infrastructure (Terraform)
Toutes les commandes doivent être lancées depuis le dossier `terraform/`.
- **Initialiser :** `terraform init`
- **Vérifier les changements :** `terraform plan`
- **Déployer le réseau/IAM :** `terraform apply`

### Kubernetes (minikube)
Le projet utilise minikube pour le développement sans frais.
- **Démarrer le cluster :** `minikube start --driver=docker --cpus=2 --memory=4096`
- **Arrêter le cluster :** `minikube stop`
- **Voir les ressources :** `kubectl get all`

---

> Note : Ce projet est actuellement en phase de développement actif. [Suivre l'avancement ici](PROGRESS.md).
>
> Les standards d'ingénierie appliqués sont documentés dans le [guide des standards](docs/engineering_standards.md).
