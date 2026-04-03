# Backlog — Quetes secondaires

Ce fichier regroupe les idees d'ameliorations et les taches non-bloquantes. Pour le suivi principal, voir [PROGRESS.md](PROGRESS.md).

---

## Priorite - Refonte API-only modulaire
- [x] Phase 0 - Baseline produit figee (matrice fonctionnalites)
- [x] Phase 0 - Scope contractuel fige (in/out du coeur produit)
- [x] Phase 1 - Architecture cible en couches avec regles de dependance
- [x] Phase 1 - Cartographie old-to-new pour migration parallele
- [x] Phase 2 - Classes metier/contrats: `AnalysisInput`, `Provider`, `TokenUsage`, `HealthStatus`, ports observabilite
- [x] Phase 2 - Brancher `ResolveProviderUseCase` dans le flux `analyze` (selection provider/modele explicite)
- [x] Phase 2 - Centraliser les appels agent non-streaming via `ExecuteAgentCallUseCase`
- [x] Phase 2 - Use cases applicatifs restants centralises (`GenerateFullResponseUseCase` + usage scripts)
- [x] Phase 3 - Adapters providers harmonises sur socle commun (retry/payload/tokens/erreurs)
- [x] Phase 3 - Observabilite decouplee via `ObservabilityGateway` (traces + metriques)
- [x] Phase 3 - Injection `LLMProviderRegistry` via composition (plus de factory globale sur le flux API)
- [x] Phase 3 - Composition API: suppression complete des singletons globaux metier
- [x] Phase 5 - Decommission legacy hors API-first (`legacy/pedantix`, `legacy/tusmo`, bots/bench ad hoc)

Reference: [docs/api_only_migration_plan.md](docs/api_only_migration_plan.md)

---

## Quick Wins (< 1h chacun)
- [x] Nettoyer `config.py` : retirer `openai_api_key` et `mistral_api_key` (dead code, jamais utilises)
- [x] Aligner le gate couverture local + CI a 90% (`make ci-local` + GitHub Actions)
- [x] Harmoniser `README.md` et `docs/features.md` avec l'architecture API-only actuelle
- [ ] Ajouter un screenshot du dashboard Grafana dans le README
- [ ] Ajouter un screenshot du dashboard Langfuse dans le README
- [ ] Tester `.devcontainer` sur GitHub Codespaces (lancement en un clic)
- [x] Aligner la stack Python projet en 3.14 (Dockerfile, CI, devcontainer, scripts Dagger/tests)

## Automatisation DX (Developer Experience)
- [x] **Makefile / Justfile** : centraliser les commandes sous des alias simples
  - `make dev` : lancer l'API FastAPI en local (uvicorn)
  - `make benchmark` : locust avec rapport HTML
  - `make monitoring` : port-forward Grafana + API
  - `make ci-local` : reproduire localement le gate qualite principal
- [x] **Script de demo** (`scripts/demo.sh`) : scenario complet pour les presentations
- [x] **One-command local** : `make demo` (build + deploy + port-forward)
- [x] **Pre-commit** : ajouter `kubeconform` pour valider les manifests K8s avant commit

## Monitoring & Observabilite
- [x] **Dashboard quotas LLM** (Grafana) : afficher les RPM/TPD consommes vs limites par modele
  - Groq Llama 3.1 8b : 30 RPM / 14.4K RPD / 500K TPD
  - Groq Llama 3.3 70b : 30 RPM / 1K RPD / 100K TPD
  - Groq GPT-OSS 120b : 30 RPM / 1K RPD / 200K TPD
  - Gemini 3.1 Flash : 15 RPM / 500 RPD / 250K TPM
- [x] **Alerting Prometheus** : P95 latence > 5s, taux erreur > 5%, quotas > 80%
- [x] **Logs centralises** : stack Loki/Promtail pour correler logs API + metriques Prometheus
- [x] **Dashboard LLM avance** : tokens in/out, cout cumule, latence par modele (Grafana)

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
