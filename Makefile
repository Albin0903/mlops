# -----------------------------------------------------------------------------
# Makefile pour le projet MLOps - LLM code analyzer
# Centralise les commandes de developpement, test et deploiement.
# -----------------------------------------------------------------------------

.PHONY: help dev build-local deploy test lint clean monitoring benchmark

# Afficher l'aide par defaut
help:
	@echo "Commandes disponibles :"
	@echo "  make dev          - Lancer l'API en mode developpement"
	@echo "  make build-local  - Build image Docker et charge dans Minikube"
	@echo "  make deploy       - Deploie les manifestes Kubernetes"
	@echo "  make test         - Lance les tests avec pytest"
	@echo "  make ci           - Lance le pipeline Dagger CI/CD local"
	@echo "  make lint         - Verifie le style avec ruff"
	@echo "  make monitoring   - Port-forward pour Grafana et l'API"
	@echo "  make benchmark    - Lance les tests de charge Locust"
	@echo "  make clean        - Nettoie les fichiers temporaires"

# Developpement local
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker et Kubernetes
build-local:
	docker build -t mlops-api:latest .
	minikube image load mlops-api:latest

deploy:
	kubectl apply -f gitops/base/ -n mlops
	kubectl apply -f k8s/monitoring/ -n mlops

# Qualite et tests
test:
	pytest --cov=app tests/

ci:
	.venv/Scripts/python scripts/dagger_ci.py

lint:
	ruff check .
	ruff format --check .

# Observabilite
monitoring:
	@echo "Accessibles sur : API (8000), Grafana (3000)"
	@powershell -Command "Start-Process kubectl -ArgumentList 'port-forward svc/mlops-api -n mlops 8000:80'; Start-Process kubectl -ArgumentList 'port-forward svc/grafana-service -n mlops 3000:3000'"

# Performance
benchmark:
	locust -f tests/locustfile.py --host http://localhost:8000 --users 5 --spawn-rate 1 --run-time 1m --headless

# Nettoyage
clean:
	@powershell -Command "Remove-Item -Recurse -Force ./**/__pycache__, ./.pytest_cache, ./.ruff_cache, ./.coverage -ErrorAction SilentlyContinue"
