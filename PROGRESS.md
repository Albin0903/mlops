# Feuille de route et suivi de projet

Ce document suit l'avancement du projet MLOps/LLMOps. Concu comme une veritable vitrine technologique CV pour un futur ingenieur Data/MLOps ex-Societe Generale, chaque sprint represente un domaine d'expertise cible : Infrastructure (Terraform/K8s), Architectures Agentiques, et DevOps industriel.

---

## Etat actuel (snapshot)
- [x] Architecture API-only en couches (`domain` / `application` / `infrastructure` / `api`)
- [x] Composition centralisee des use cases dans `app/infrastructure/composition.py`
- [x] Providers actifs: Groq, Gemini, Ollama (avec alias provider)
- [x] Gate qualite alignee local + CI (`make ci-local` et workflow GitHub)
- [x] Couverture enforcee: 90% minimum, couverture mesuree ~98%

## Plan refonte API-only (transversal)
- [x] Phase 0 - Baseline produit figee (analyze, health, providers, observabilite, CI, container)
- [x] Phase 0 - Scope contractuel fige (coeur API-first vs legacy hors coeur)
- [x] Phase 1 - Architecture cible validee (modular monolith en couches)
- [x] Phase 1 - Cartographie old-to-new formalisee pour migration parallele
- [x] Phase 2 - Classes metier et ports/contracts principaux (provider, prompt, token usage, observabilite)
- [x] Phase 2 - Resolution provider/model centralisee dans le flux applicatif `analyze`
- [x] Phase 2 - Appels agent non-streaming centralises via `ExecuteAgentCallUseCase`
- [x] Phase 2 - Centralisation complete des use cases applicatifs (`GenerateFullResponseUseCase` inclus)
- [x] Phase 3 - Composition API finalisee sans singletons metier globaux
- [x] Phase 3 - Finaliser observabilite decouplee du flux principal
- [x] Phase 3 - Injection provider registry via composition (flux API sans factory globale)
- [x] Phase 3 - Adapters providers harmonises sur socle commun (`app/services/llm/common.py`)
- [ ] Phase 4 - Rationalisation outillage/dependances
- [ ] Phase 5 - Refonte tests + decommission legacy
- [ ] Phase 6 - Cutover final et stabilisation release

Reference contrat: [docs/api_only_migration_plan.md](docs/api_only_migration_plan.md)

---

## Sprint 1 : Infrastructure Cloud & IaC
*Competences visees : Terraform, Kubernetes, Cloud Architecture*

### Terraform (modules)
- [x] Structure modulaire : `terraform/modules/{vpc, iam, cluster}`
- [x] Backend S3 distant pour l'etat Terraform
- [x] Module VPC : reseau, sous-reseaux prives/publics
- [x] Module IAM : Service Account avec privileges restreints
- [x] Module Cluster : provisionnement EKS (code valide)
- [x] Migration vers minikube (local) pour eviter les couts EKS (~70$/mois)

### Kubernetes
- [x] Cluster minikube + contexte kubectl
- [x] Ingress Controller NGINX
- [x] Manifests de deploiement (Deployment, Service, Ingress)
- [x] Dockerfile multi-stage, non-root, healthcheck
- [x] Script d'automatisation `scripts/manage_infra.py`

---

## Sprint 2 : Application LLM & DevSecOps
*Competences visees : Python async, LLM integration, testing, securite*

### FastAPI & LLM
- [x] API FastAPI 100% async avec streaming SSE
- [x] Groq : multi-modele (Llama 8b instant, 70b versatile, GPT-OSS 120b)
- [x] Gemini : `gemini-3.1-flash-lite-preview` avec Thinking Mode
- [x] Routing dynamique par provider (`groq`, `instant`, `medium`, `gpt`, `gemini`, `ollama*`)
- [x] Retry avec backoff exponentiel (Tenacity)
- [x] Prompts systeme optimises (reduction tokens ~30%)
- [x] Validation stricte avec Pydantic

### Conteneurisation
- [x] Dockerfile multi-etapes (builder + runtime)
- [x] Utilisateur non-root, .dockerignore, labels OCI
- [x] HEALTHCHECK integre

### Observabilite LLM (Langfuse)
- [x] Tracing des prompts, reponses et latence
- [x] Suivi tokens (entree/sortie) et cout par requete
- [x] Traces nommees par endpoint et provider

### Tests automatises (Pytest)
- [x] Configuration pytest + pytest-cov
- [x] Tests endpoints avec `httpx.AsyncClient`
- [x] Tests service LLM avec mocking
- [x] Tests schemas Pydantic
- [x] Tests health check et config
- [x] Couverture gate CI/local : 90% (mesuree ~98%)

---

## Sprint 3 : CI/CD moderne & GitOps
*Competences visees : GitHub Actions, ArgoCD, Git Flow*

### CI GitHub Actions
- [x] 4 jobs paralleles : Lint (Ruff) | Tests (Pytest) | Security (Trivy) | Build & Push (GHCR)
- [x] Cache pip et Docker layers (GHA cache)
- [x] Build conditionnel (GHCR sur main uniquement)
- [x] Badges CI dans le README

### Workflow Git
- [x] Git Flow simplifie (main -> develop -> feature/*)
- [x] Pull Requests avec review obligatoire
- [x] Protection de la branche main

### GitOps ArgoCD
- [x] Manifests GitOps (`gitops/base/`, `gitops/overlays/minikube/`)
- [x] Auto-sync + self-heal
- [x] Documentation (`docs/argocd_gitops.md`)
- [ ] Schema du flux GitOps (Excalidraw/draw.io)
- [ ] Strategie Blue/Green ou Canary (Argo Rollouts)

### Environnement de dev (.devcontainer)
- [x] Configuration VS Code / GitHub Codespaces
- [x] Extensions pre-installees, `postCreateCommand`
- [ ] Validation sur Codespaces

---

## Sprint 4 : Monitoring & Load Testing
*Competences visees : Prometheus, Grafana, SRE, performance engineering*

### Monitoring (Prometheus & Grafana)
- [x] Deployment Prometheus + Grafana sur K8s
- [x] Instrumentation FastAPI (`prometheus-fastapi-instrumentator`)
- [x] Metriques custom LLM : `llm_requests_total`, `llm_tokens_total`, `llm_latency_seconds`, `llm_errors_total`
- [x] Dashboard Grafana as Code (ConfigMap versionne)
- [x] Dashboard : total HTTP requests, status codes, latence moyenne, request rate
- [x] Dashboard : quotas LLM (RPM/TPD restants par modele)
- [x] Dashboard LLM avance : tokens in/out, cout cumule, latence par modele
- [x] Alerting Prometheus (latence P95 > 5s, taux erreur > 5%)
- [x] Logs centralises (Loki/Promtail)

### Tests de charge (Locust)
- [x] Fichier `tests/locustfile.py` avec scenarios multi-provider
- [x] Benchmark 50% charge max, respect des quotas free tier
- [x] Resultats : Groq Instant ~264ms (0% erreur), Gemini ~4s (28% erreur)
- [ ] Scenarios avances : montee en charge progressive, burst, endurance
- [ ] Rapport HTML automatise dans la CI
- [ ] Ajustement replicas/rate limiting en fonction des resultats

---

## Sprint 5 : CI locale & Automatisation
*Competences visees : Dagger, DX, productivite*

### CI locale (Dagger)
- [x] Script `scripts/dagger_ci.py` (lint + test + build)
- [ ] Validation complete et documentation
- [ ] Integration dans le workflow de dev quotidien

### Automatisation des processus
- [x] Makefile/Justfile : `make dev`, `make deploy`, `make benchmark`, `make monitoring`
- [x] Script de demo rapide (`scripts/demo.sh`)
- [x] Script one-command : build + load + deploy + port-forward
- [x] Pre-commit : ajouter validation des manifests K8s (kubeval/kubeconform)

---

## Sprint 6 : Ingénierie Agentique & Workflows Autonomes (Pédantix & Tusmo)
*Competences visees : Function Calling, ReAct Agents, Automatisation (RPA/Selenium), LLOps avance*

### Refactoring Agentique (Pédantix)
- [ ] Transformer la logique `solve_pedantix.py` en framework Agentique (ReAct).
- [ ] Implementer le Function Calling dans `app/services/llm_service.py` (`search_wikipedia`, `guess_word`).
- [ ] Monitorer les traces de reflexion et les appels d'outils via Langfuse.

### Module Tusmo (Solveur IA & RPA)
- [ ] Integrer le moteur d'entropie (`tusmo/final.py`) comme service backend `app/services/tusmo_service.py`.
- [ ] Creer des outils interactifs (SQL/regex) permettant a l'IA de reduire l'espace de recherche.
- [ ] Connecter le bot automatise Selenium (`tusmo/solve.py`) pour jouer les parties de maniere 100% autonome.
- [ ] Dashboard Grafana (Metriques MLOps) : tracker la performance de l'agent (taux de succes, nombre de coups moyen).

---

## Sprint 7 : Excellence Operationnelle & AI Reliability
*Competences visees : AI safety, caching, supply chain security*

### Performance & FinOps (Caching)
- [ ] Redis sur Kubernetes (Helm)
- [ ] Semantic Cache (requetes identiques = pas de re-appel LLM)
- [ ] Dashboard Grafana : economie cout/latence via cache
- [ ] Rapport FinOps : comparatif EKS vs minikube, cout par requete

### AI Quality & Guardrails
- [ ] Guardrails AI : blocage injection de prompts
- [ ] Prompt versioning (Langfuse experiments)
- [ ] LLM-as-a-judge dans la CI (DeepEval/Ragas)

### Supply Chain Security (SecOps)
- [ ] Signature des images Docker (Cosign) dans GitHub Actions
- [ ] SBOM (Software Bill of Materials) via Syft
- [ ] Migration secrets : `.env` -> HashiCorp Vault / External Secrets Operator

### Progressive Delivery
- [ ] Argo Rollouts : deploiement Canary (10% -> 50% -> 100%)
- [ ] AnalysisTemplate : rollback auto si taux erreur > 1%

---

## Sprint 8 : Valorisation & Portfolio
*Competences visees : communication technique, documentation pro*

### Documentation
- [ ] README en anglais (version portfolio internationale)
- [ ] Schema d'architecture (Excalidraw)
- [ ] Compromis techniques documentes (FastAPI vs Flask, Groq vs OpenAI, etc.)

### Showcase
- [ ] MkDocs + GitHub Pages (Material theme)
- [ ] Export Swagger/Redoc statique
- [ ] Screenshots Grafana + Langfuse dans le README

### Packaging
- [x] Nettoyage code (dead code, TODOs, type hints complets)
- [ ] `CONTRIBUTING.md`
- [ ] Compatibilite multi-OS verifiee (`pathlib`)

---

## Bonnes pratiques recurrentes
- [ ] FinOps : `terraform destroy` apres chaque session
- [ ] Securite : zero secret dans Git
- [ ] Qualite : type hints + docstrings sur chaque fonction
- [ ] Git : commits atomiques (`feat:`, `fix:`, `docs:`, `ci:`)
- [ ] Linting : Ruff avant chaque commit (pre-commit)

