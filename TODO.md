# TODO - Idées d'améliorations techniques

Ce fichier regroupe les suggestions d'optimisations et de fonctionnalités avancées pour renforcer le projet MLOps.

## 🚀 Automatisation DX (Developer Experience)
- [ ] **Pipeline Dagger local complet** : Automatiser le cycle `docker-env` -> `build` -> `rollout restart` pour ne plus avoir à taper les commandes manuellement après une modif de code.
- [ ] **Makefile / Justfile** : Centraliser toutes les commandes (ArgoCD, Port-forward, Tests, Dagger) sous des alias simples (ex: `make dev`, `make deploy-infra`).

## 📊 Observabilité & Qualité
- [ ] **Persistent Dashboards as Code** : Continuer d'extraire les dashboards créés manuellement dans Grafana pour les versionner dans `k8s/monitoring/dashboards.yaml`.
- [ ] **Logs centralisés** : Ajouter une stack Loki/Promtail pour corréler les logs de l'API avec les métriques Prometheus.

## 💰 FinOps & Quotas (Groq & Gemini)
- [ ] **Suivi des quotas (Free Tier)** :
    - **Groq Llama 3.1 8b**: 30 RPM / 14.4K RPD / 500K TPD.
    - **Groq Llama 3.3 70b**: 30 RPM / 1K RPD / 100K TPD.
    - **Groq GPT-OSS 120b**: 30 RPM / 1K RPD / 200K TPD.
    - **Gemini 3.1 Flash**: 15 RPM / 500 RPD / 250K TPM.
- [ ] **Semantic Caching** : Utiliser Redis pour éviter de payer deux fois pour la même question/analyse de code.

## 🔐 SecOps
- [ ] **SBOM & Signatures** : Automatiser la génération de SBOM (Syft) et la signature des images (Cosign) dans la CI GitHub Actions.
- [ ] **Secrets Management** : Migrer du fichier `.env` vers un outil comme HashiCorp Vault ou AWS Secrets Manager (intégré via External Secrets Operator sur K8s).

---
*Note : Pour le suivi global du projet, voir [PROGRESS.md](PROGRESS.md).*
