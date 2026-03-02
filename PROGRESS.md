# Feuille de route et suivi de projet

Ce document suit le plan de 24 semaines pour construire une infrastructure MLOps/LLMOps de classe production.

## Sprint 1 : Infrastructure cloud & IaC (Semaines 1-6)
*Objectif : Prouver vos compétences en ingénierie cloud avec Terraform et Kubernetes.*

### Semaines 1-2 : Fondations & bootstrap
- [ ] Créer un compte Cloud (GCP/AWS/Azure) et configurer le CLI (gcloud/aws/az)
- [ ] Créer manuellement un bucket de stockage (GCS/S3) pour le backend Terraform
- [ ] Configurer le `backend.tf` pour utiliser le bucket distant
- [ ] Initialiser la structure modulaire : `terraform/modules/{vpc, cluster}`

### Semaines 3-4 : Réseau & cluster K8s (IaC)
- [ ] Module VPC : Définir le réseau, les sous-réseaux privés et publics
- [ ] Module IAM : Créer un Service Account avec privilèges restreints pour le cluster
- [ ] Module Cluster : Provisionnement GKE/EKS (instances e2-medium ou t3.medium)
- [ ] Exécuter `terraform apply` et vérifier la création via la console Cloud
- [ ] Configurer `outputs.tf` pour extraire l'IP et les certificats du cluster

### Semaines 5-6 : Kubernetes & connectivité (Masterclass)
- [ ] Installer kubectl et configurer le contexte de connexion au cluster
- [ ] Déployer un Ingress Controller (NGINX) via Helm
- [ ] Créer et déployer les manifests `k8s/hello-world.yaml` (Deployment, Service ClusterIP, Ingress)
- [ ] Vérifier l'accès à l'application via l'URL publique de l'Ingress
- [ ] Finaliser le script Python `scripts/manage_infra.py` pour automatiser `apply` et `destroy`

---

## Sprint 2 : Application LLM & DevSecOps (Semaines 7-12)
*Objectif : Développer un code Python robuste, optimisé et sécurisé.*

### Semaines 7-8 : FastAPI & intégration LLM
- [ ] Initialiser le projet FastAPI avec des gestionnaires `async def`
- [ ] Intégrer l'API Mistral ou OpenAI
- [ ] Implémenter des tentatives (Retries) avec backoff exponentiel (Résilience)
- [ ] Ajouter des modèles Pydantic stricts pour la validation entrée/sortie

### Semaine 9 : Conteneurisation avancée
- [ ] Écrire un Dockerfile multi-étapes (taille optimisée)
- [ ] Implémenter la sécurité avec un utilisateur non-root dans Docker
- [ ] Configurer le fichier `.dockerignore`

### Semaines 10-12 : Observabilité LLM (Langfuse)
- [ ] Intégrer le SDK Langfuse
- [ ] Logger les prompts, les réponses et la latence
- [ ] Suivre l'utilisation des tokens (entrée/sortie) et calcul du coût par requête

---

## Sprint 3 : CI/CD moderne & GitOps (Semaines 13-18)
*Objectif : Passer des déploiements "push" vers le "GitOps" (pull).*

### Semaines 13-15 : Intégration continue (CI)
- [ ] Configurer le workflow GitHub Actions
- [ ] Étape : Linting (Ruff)
- [ ] Étape : Tests unitaires (Pytest)
- [ ] Étape : Scan de sécurité (Trivy)
- [ ] Étape : Build & push vers un registre (GHCR/DockerHub)

### Semaines 16-18 : Déploiement continu (CD) avec ArgoCD
- [ ] Installer ArgoCD sur le cluster Kubernetes
- [ ] Créer un dépôt "GitOps" pour les manifestes
- [ ] Connecter ArgoCD au dépôt pour la synchronisation automatique
- [ ] Implémenter une logique de déploiement Blue/Green ou Canary (Optionnel)

---

## Sprint 4 : Monitoring & valorisation (Semaines 19-24)
*Objectif : Excellence opérationnelle et documentation professionnelle.*

### Semaines 19-21 : Monitoring de l'infrastructure
- [ ] Déployer Prometheus via Helm Charts
- [ ] Déployer Grafana
- [ ] Créer des tableaux de bord : Utilisation CPU/RAM, taux de 4xx/5xx, requêtes/sec

### Semaines 22-24 : Portfolio & system design
- [ ] Créer un schéma d'architecture professionnel (Excalidraw/Draw.io)
- [ ] Documenter les compromis techniques (FastAPI vs Flask, ArgoCD vs GH Actions)
- [ ] Finaliser le README.md (en Anglais pour le portfolio, mais documenté ici)
- [ ] Ajouter un rapport "FinOps" (Stratégies d'optimisation des coûts implémentées)

---

### Tâches récurrentes et bonnes pratiques
- [ ] FinOps : S'assurer que terraform destroy est lancé après chaque session.
- [ ] Sécurité : Aucun secret dans Git (utiliser Secrets Manager/GitHub Secrets).
- [ ] Qualité du code : Typage (type hinting) et documentation pour chaque fonction.
- [ ] Compatibilité : Garantir le fonctionnement multi-OS (Windows/Linux) via `pathlib` et scripts Python.
- [ ] Linting : Exécution systématique de Ruff avant chaque commit.
- [ ] Infrastructure : Validation des fichiers Terraform avec `terraform validate`.
- [ ] Kubernetes : Utilisation de Helm pour structurer les déploiements complexes.
