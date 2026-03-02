# Scalable & Secure LLM Code Analyzer (Production-Grade)

## Objectif du Projet
Concevoir, déployer et monitorer une API d'analyse de code alimentée par des LLMs. Ce projet met l'accent sur l'**Excellence de l'Infrastructure** (Haute Disponibilité, Sécurité, Maîtrise des Coûts, CI/CD Moderne) plutôt que sur la seule performance du modèle d'IA.

## Pile Technique
- **Langages :** Python, FastAPI (Asynchrone)
- **Infrastructure :** Terraform, Kubernetes (GKE/EKS)
- **CI/CD :** GitHub Actions, ArgoCD (GitOps)
- **Observabilité :** Prometheus, Grafana, Langfuse (Suivi LLM)
- **Sécurité :** Trivy, Builds Docker multi-étapes

## Fonctionnalités Clés
- **API Asynchrone :** Analyse de code à haute concurrence.
- **Workflow GitOps :** Déploiements automatisés via ArgoCD.
- **Observabilité Complète :** Suivi des tokens, de la latence, des coûts et de la santé de l'infra.
- **Sécurité de Classe Production :** Conteneurs non-root et scan de vulnérabilités.

---
> Note : Ce projet est actuellement en phase de développement actif suivant une feuille de route de 24 semaines. [Suivre l'avancement ici](PROGRESS.md).
>
> Les standards de développement et d'ingénierie appliqués à ce projet sont documentés dans le guide des [Standards d'Ingénierie](docs/engineering_standards.md).
