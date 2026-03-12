# Backlog — Quetes secondaires

Ce fichier regroupe les idees d'ameliorations et les taches non-bloquantes. Pour le suivi principal, voir [PROGRESS.md](PROGRESS.md).

---

## Quick Wins (< 1h chacun)
- [ ] Nettoyer `config.py` : retirer `openai_api_key` et `mistral_api_key` (dead code, jamais utilises)
- [ ] Ajouter un screenshot du dashboard Grafana dans le README
- [ ] Ajouter un screenshot du dashboard Langfuse dans le README
- [ ] Tester `.devcontainer` sur GitHub Codespaces (lancement en un clic)
- [ ] Corriger le Dockerfile : Python 3.12 dans le build vs 3.13 dans la CI (aligner)

## Automatisation DX (Developer Experience)
- [ ] **Makefile / Justfile** : centraliser les commandes sous des alias simples
  - `make dev` : build + load + deploy + port-forward
  - `make benchmark` : locust avec rapport HTML
  - `make monitoring` : port-forward Grafana + API
  - `make ci` : lancer le pipeline Dagger local
- [ ] **Script de demo** (`scripts/demo.sh`) : scenario complet pour les presentations
- [ ] **Pre-commit** : ajouter `kubeconform` pour valider les manifests K8s avant commit

## Monitoring & Observabilite
- [ ] **Dashboard quotas LLM** (Grafana) : afficher les RPM/TPD consommes vs limites par modele
  - Groq Llama 3.1 8b : 30 RPM / 14.4K RPD / 500K TPD
  - Groq Llama 3.3 70b : 30 RPM / 1K RPD / 100K TPD
  - Groq GPT-OSS 120b : 30 RPM / 1K RPD / 200K TPD
  - Gemini 3.1 Flash : 15 RPM / 500 RPD / 250K TPM
- [ ] **Alerting Prometheus** : P95 latence > 5s, taux erreur > 5%, quotas > 80%
- [ ] **Logs centralises** : stack Loki/Promtail pour correler logs API + metriques Prometheus
- [ ] **Dashboard LLM avance** : tokens in/out, cout cumule, latence par modele (Grafana)

## AI Engineering
- [ ] **Semantic Cache** (Redis) : eviter de payer deux fois la meme requete LLM
- [ ] **Guardrails AI** : blocage des injections de prompts et contenu non-souhaite
- [ ] **Prompt versioning** : utiliser Langfuse Experiments pour A/B testing de prompts
- [ ] **LLM-as-a-judge** : evaluation automatique de la qualite des reponses dans la CI (DeepEval)

## SecOps
- [ ] **SBOM** (Syft) : generation automatique dans GitHub Actions
- [ ] **Image signing** (Cosign) : signer les images Docker dans la CI
- [ ] **Secrets Management** : migrer `.env` vers Vault ou External Secrets Operator (K8s)
- [ ] **Rate limiting** : implementer un rate limiter dans FastAPI (slowapi) pour proteger les quotas

## Performance & FinOps
- [ ] **Scenarios Locust avances** :
  - Montee en charge progressive (1 -> 20 users)
  - Burst de trafic (50 requetes simultanees)
  - Endurance (charge constante 30 min)
- [ ] **Rapport FinOps** : comparatif cout EKS vs minikube, cout par requete LLM
- [ ] **Replicas auto** : HPA (Horizontal Pod Autoscaler) base sur la latence P95
- [ ] **Helm Charts** : packager le deploiement API + monitoring pour reutilisation

## Portfolio & Documentation
- [ ] **README anglais** : version portfolio pour postuler a l'international
- [ ] **Schema d'architecture** : diagramme Excalidraw (flux user -> API -> LLM -> response)
- [ ] **MkDocs + GitHub Pages** : documentation hebergee avec theme Material
- [ ] **CONTRIBUTING.md** : guide de contribution (workflow Git, conventions)
- [ ] **Rapport de performance** : documenter les resultats Locust avec graphiques dans le README

---

*Note : les taches marquees comme prioritaires dans PROGRESS ont la precedence sur ce backlog.*
