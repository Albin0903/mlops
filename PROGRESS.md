# Feuille de route et suivi de projet

Ce document suit le plan pour construire une infrastructure MLOps/LLMOps de classe production.

---

## Sprint 1 : Infrastructure Cloud & IaC
*Objectif : Prouver ses compétences en ingénierie cloud avec Terraform et Kubernetes.*

### Fondations & bootstrap
- [x] Créer un compte Cloud (GCP/AWS/Azure) et configurer le CLI (gcloud/aws/az)
- [x] Créer manuellement un bucket de stockage (GCS/S3) pour le backend Terraform
- [x] Configurer le `backend.tf` pour utiliser le bucket distant
- [x] Initialiser la structure modulaire : `terraform/modules/{vpc, cluster}`

### Réseau & cluster K8s (IaC)
- [x] Module VPC : Définir le réseau, les sous-réseaux privés et publics
- [x] Module IAM : Créer un Service Account avec privilèges restreints pour le cluster
- [x] Module Cluster : Provisionnement EKS (code terraform écrit et validé)
- [x] Exécuter `terraform apply` et vérifier la création via la console Cloud
- [x] Configurer `outputs.tf` pour extraire l'IP et les certificats du cluster
- [x] Migration vers minikube (local) pour éviter les coûts EKS (~70$/mois)

### Kubernetes & connectivité (Masterclass)
- [x] Démarrer minikube et configurer le contexte kubectl
- [x] Déployer un Ingress Controller (NGINX) via Helm
- [x] Créer et déployer les manifests `k8s/hello-world.yaml` (Deployment, Service ClusterIP, Ingress)
- [x] Créer un `Dockerfile` professionnel (Multi-stage, Non-root, .dockerignore)
- [x] Finaliser le script Python `scripts/manage_infra.py` pour automatiser `apply` et `destroy`

---

## Sprint 2 : Application LLM & DevSecOps
*Objectif : Développer un code Python robuste, optimisé et sécurisé.*

### FastAPI & intégration LLM
- [x] Initialiser le projet FastAPI avec des gestionnaires `async def`
- [x] Intégrer l'API Groq (Llama 3.3 70B) en streaming asynchrone
- [x] Intégrer l'API Gemini (gemini-3.1-flash-lite) en tant que provider alternatif
- [x] Implémenter des tentatives (Retries) avec backoff exponentiel (Résilience)
- [x] Ajouter des modèles Pydantic stricts pour la validation entrée/sortie
- [x] Optimiser les system prompts pour réduire la consommation de tokens
- [x] Créer un script de test streaming asynchrone (`scripts/test_streaming.py`)

### Conteneurisation avancée
- [x] Écrire un Dockerfile multi-étapes (taille optimisée)
- [x] Implémenter la sécurité avec un utilisateur non-root dans Docker
- [x] Configurer le fichier `.dockerignore`

### Observabilité LLM (Langfuse)
- [x] Intégrer le SDK Langfuse dans `app/services/llm_service.py`
- [x] Logger les prompts, les réponses et la latence de chaque appel LLM
- [x] Suivre l'utilisation des tokens (entrée/sortie) et calcul du coût par requête
- [x] Créer des traces nommées pour chaque endpoint (`/analyze/doc`, `/analyze/question`)
- [ ] Ajouter un screenshot du dashboard Langfuse dans le README

### Tests automatisés (Pytest)
- [x] Configurer `pytest` et `pytest-cov` dans `requirements-dev.txt`
- [x] Écrire les tests des endpoints FastAPI avec `httpx.AsyncClient` (`tests/test_api.py`)
- [x] Écrire les tests du service LLM avec mocking de l'API Groq (`tests/test_llm_service.py`)
- [x] Écrire les tests de validation des schémas Pydantic (`tests/test_schemas.py`)
- [x] Écrire les tests du health check et de la configuration (`tests/test_health.py`)
- [x] Atteindre un taux de couverture ≥ 70% (99% atteint)
- [x] Ajouter un badge de couverture dans le README

---

## Sprint 3 : CI/CD moderne & GitOps
*Objectif : Passer des déploiements "push" vers le "GitOps" (pull).*

### Intégration continue (CI) — GitHub Actions
- [x] Configurer le workflow `.github/workflows/ci.yml`
  - [x] Étape : Linting avec Ruff (vérification de style et erreurs)
  - [x] Étape : Tests unitaires avec Pytest + couverture
  - [x] Étape : Scan de sécurité de l'image Docker avec Trivy
  - [x] Étape : Build & push de l'image vers GHCR (GitHub Container Registry)
- [x] Ajouter des badges CI (build status, coverage, security) dans le README

### Workflow Git professionnel
- [x] Créer la branche `develop` depuis `main`
- [x] Adopter un workflow Git Flow simplifié (`main` → `develop` → `feature/*`)
- [x] Créer des Pull Requests pour chaque feature (historique visible par les recruteurs)
- [x] Configurer des règles de protection sur `main` (review requise, CI verte)

### Deploiement continu (CD) avec ArgoCD
- [x] Installer ArgoCD sur le cluster Kubernetes (minikube)
- [x] Creer les manifests GitOps (`gitops/base/`, `gitops/overlays/minikube/`)
- [x] Connecter ArgoCD au repo pour la synchronisation automatique (auto-sync + self-heal)
- [x] Documenter le flux GitOps (`docs/argocd_gitops.md`)
- [ ] Optionnel : separer le dossier GitOps dans un repo dedie
- [ ] Implementer une logique de deploiement Blue/Green ou Canary
- [ ] Ajouter un schema du flux GitOps (draw.io)

### Environnement de développement (.devcontainer)
- [x] Créer `.devcontainer/devcontainer.json` (VS Code / GitHub Codespaces)
- [x] Configurer les extensions pré-installées (Python, Ruff, Docker)
- [x] Ajouter un `postCreateCommand` pour installer les dépendances automatiquement
- [ ] Tester le lancement en un clic via Codespaces

---

## Sprint 4 : CI/CD 2.0 & Monitoring Avancé
*Objectif : Excellence opérationnelle avec Dagger, DVC et monitoring de drift.*

### CI/CD "Local-first" (Dagger)
- [ ] Initialiser le pipeline Dagger en Python (`scripts/dagger_ci.py`)
- [ ] Porter les étapes de Lint (Ruff) et Test (Pytest) sur Dagger
- [ ] Automatiser le build de l'image Docker via Dagger
- [ ] Documenter comment lancer la CI localement sans GitHub Actions

### Data Versioning & MLOps Maturity
- [ ] Initialiser DVC pour le versionning des données/modèles
- [ ] Configurer un remote storage (S3/GCS) pour DVC
- [ ] Intégrer Evidently AI pour la détection du drift de données
- [ ] Ajouter Great Expectations pour la validation de la qualité des données

### Monitoring de l'infrastructure (Prometheus & Grafana)
- [ ] Créer des Helm Charts personnalisés pour le déploiement de l'API (`helm/mlops-api/`)
- [ ] Déployer Prometheus via Helm Charts sur minikube
- [ ] Déployer Grafana via Helm Charts sur minikube
- [ ] Instrumenter FastAPI avec `prometheus-fastapi-instrumentator` (métriques HTTP)
- [ ] Créer des métriques custom : latence LLM, tokens consommés, coût par requête
- [ ] Créer des tableaux de bord Grafana :
  - [ ] Dashboard infra : CPU/RAM, requêtes/sec, taux de 4xx/5xx, latence P50/P95/P99
  - [ ] Dashboard LLM : tokens in/out, coût cumulé, latence par modèle
- [ ] Configurer des alertes Prometheus (ex : latence P95 > 5s, taux d'erreur > 5%)
- [ ] Ajouter un screenshot des dashboards dans le README

### MLflow — Tracking d'expériences
- [ ] Déployer un serveur MLflow (local ou conteneurisé)
- [ ] Intégrer MLflow dans le service LLM pour tracker les expériences
  - [ ] Logger les paramètres : modèle, temperature, max_tokens, system prompt
  - [ ] Logger les métriques : latence, tokens utilisés, coût
  - [ ] Logger les artefacts : exemples de prompts/réponses
- [ ] Créer des expériences pour comparer différentes configurations de prompts
- [ ] Documenter l'utilisation de MLflow dans le README

### Tests de charge (Locust)
- [ ] Créer un fichier `locustfile.py` pour simuler du trafic sur l'API
- [ ] Définir des scénarios de test :
  - [ ] Scénario 1 : Montée en charge progressive (10 → 100 utilisateurs)
  - [ ] Scénario 2 : Pic de trafic (burst de 200 requêtes)
  - [ ] Scénario 3 : Endurance (charge constante pendant 30 min)
- [ ] Identifier les goulots d'étranglement (latence, erreurs, saturation)
- [ ] Documenter les résultats avec graphiques (Locust dashboard) dans le README
- [ ] Ajuster la configuration (workers, replicas, rate limiting) en conséquence

---

## Sprint 5 : Valorisation & Portfolio
*Objectif : Documentation professionnelle et packaging du projet pour le CV.*

### Documentation technique
- [ ] Rédiger le README.md complet en anglais (version portfolio internationale)
- [ ] Créer un schéma d'architecture professionnel (Excalidraw/Draw.io)
  - [ ] Vue globale : flux de données end-to-end (user → API → LLM → response)
  - [ ] Vue infra : Terraform → K8s → ArgoCD → Monitoring
- [ ] Documenter les compromis techniques (design decisions) :
  - [ ] FastAPI vs Flask (performance async, typing natif)
  - [ ] Groq vs OpenAI (latence, coût, open-source)
  - [ ] ArgoCD vs GitHub Actions CD (GitOps vs push-based)
  - [ ] Minikube vs EKS (coût vs production-readiness)

### Rapport FinOps
- [ ] Calculer le coût mensuel de la stack en production (AWS EKS)
  - [ ] Cluster EKS : compute, networking, storage
  - [ ] API LLM : coût par requête, projection mensuelle
  - [ ] Monitoring : stockage Prometheus, rétention Grafana
- [ ] Documenter les stratégies d'optimisation implémentées :
  - [ ] Migration EKS → minikube pour le dev (économie ~70$/mois)
  - [ ] Optimisation des prompts (réduction tokens de ~30%)
  - [ ] `terraform destroy` automatique après chaque session
  - [ ] Rate limiting et circuit breaker pour contrôler les coûts LLM
- [ ] Créer un tableau comparatif coût/performance

### Showcase & Portfolio (GitHub Pages)
- [ ] Configurer MkDocs avec le thème Material pour une documentation "classe production"
- [ ] Automatiser le déploiement des rapports de couverture (Pytest HTML) via GitHub Actions
- [ ] Exporter et héberger la documentation API statique (Swagger/Redoc) pour consultation hors-ligne
- [ ] Intégrer les schémas d'architecture haute résolution et interactifs dans la documentation
- [ ] Automatiser l'hébergement des rapports de qualité et de drift (Evidently AI / Great Expectations)

### Packaging final
- [ ] Passer en revue et nettoyer l'ensemble du code (dead code, TODOs)
- [ ] S'assurer que le typage (type hinting) est complet sur chaque fonction
- [ ] Vérifier que chaque module a une docstring claire
- [ ] Créer un `Makefile` ou un `justfile` pour les commandes courantes
- [ ] Ajouter un fichier `CONTRIBUTING.md` (bonnes pratiques, workflow Git)
- [ ] Vérifier la compatibilité multi-OS (Windows/Linux) via `pathlib`
- [ ] Préparer un script de démo rapide (`scripts/demo.sh`) pour les présentations

---

## Sprint 6 : Excellence Opérationnelle & AI Reliability
*Objectif : Atteindre un niveau expert en résilience, évaluation IA et sécurité.*

### Progressive Delivery (Argo Rollouts)
- [ ] Installer Argo Rollouts sur le cluster minikube
- [ ] Configurer un déploiement Canary pour l'API (10% -> 50% -> 100%)
- [ ] Implémenter un AnalysisTemplate pour automatiser le rollback si le taux d'erreur > 1% durant le déploiement

### Évaluation & Guardrails (AI Quality)
- [ ] Intégrer **Ragas** ou **DeepEval** pour mesurer la "Faithfulness" et "Relevance" des réponses
- [ ] Mettre en place des **Guardrails AI** pour bloquer les injections de prompts (Prompt Injection)
- [ ] Automatiser l'étape "LLM-as-a-judge" dans le pipeline CI (Dagger)

### Performance & FinOps Avancé (Caching)
- [ ] Déployer une instance **Redis** sur Kubernetes via Helm
- [ ] Implémenter un **Semantic Cache** (via Redis ou GPTCache) pour réduire la latence sur les requêtes identiques
- [ ] Mesurer et dashboarder (Grafana) l'économie de coût et de latence générée par le cache

### Supply Chain Security (SecOps)
- [ ] Configurer la signature des images Docker avec **Cosign** dans GitHub Actions
- [ ] Générer et publier un **SBOM** (Software Bill of Materials) via Syft pour chaque build
- [ ] Mettre en place un scan de vulnérabilités bloquant (Trivy) pour les dépendances Python et OS

---

## Tâches récurrentes et bonnes pratiques
- [ ] **FinOps :** S'assurer que `terraform destroy` est lancé après chaque session
- [ ] **Sécurité :** Aucun secret dans Git (utiliser Secrets Manager / GitHub Secrets)
- [ ] **Qualité du code :** Typage (type hinting) et documentation pour chaque fonction
- [ ] **Compatibilité :** Garantir le fonctionnement multi-OS (Windows/Linux) via `pathlib`
- [ ] **Linting :** Exécution systématique de Ruff avant chaque commit
- [ ] **Infrastructure :** Validation des fichiers Terraform avec `terraform validate`
- [ ] **Kubernetes :** Utilisation de Helm pour structurer les déploiements complexes
- [ ] **Git :** Commits atomiques avec messages conventionnels (`feat:`, `fix:`, `docs:`, `ci:`)
