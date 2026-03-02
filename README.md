# Scalable & secure LLM code analyzer

## Objectif
Concevoir, déployer et monitorer une API d'analyse de code alimentée par des LLMs. Ce projet met l'accent sur l'**excellence de l'infrastructure** (haute disponibilité, sécurité, maitrise des coûts, CI/CD moderne) plutôt que sur la seule performance du modèle d'IA.

## Pile technique
- **Langages :** Python, FastAPI (Asynchrone)
- **Infrastructure :** Terraform, Kubernetes (GKE/EKS)
- **CI/CD :** GitHub Actions, ArgoCD (GitOps)
- **Observabilité :** Prometheus, Grafana, Langfuse (Suivi LLM)
- **Sécurité :** Trivy, Builds Docker multi-étapes

## Fonctionnalités clés
- **API asynchrone :** Analyse de code à haute concurrence.
- **Workflow GitOps :** Déploiements automatisés via ArgoCD.
- **Observabilité complète :** Suivi des tokens, de la latence, des coûts et de la santé de l'infra.
- **Sécurité de classe production :** Conteneurs non-root et scan de vulnérabilités.

---
> Note : Ce projet est actuellement en phase de développement actif suivant une feuille de route de 24 semaines. [Suivre l'avancement ici](PROGRESS.md).
>
> Les standards de développement et d'ingénierie appliqués à ce projet sont documentés dans le guide des [standards d'ingénierie](docs/engineering_standards.md).
