# -----------------------------------------------------------------------------
# Makefile - workflow local standardise (API-only)
# -----------------------------------------------------------------------------

.PHONY: help install dev test test-fast lint format quality ci-local build-local deploy monitoring benchmark demo up-local clean

PYTHON ?= python

help:
	@echo "Commandes disponibles :"
	@echo "  make install      - Installe les dependances et les hooks pre-commit"
	@echo "  make dev          - Lance l'API en mode developpement"
	@echo "  make test         - Lance tous les tests avec couverture"
	@echo "  make test-fast    - Lance un sous-ensemble de tests rapides"
	@echo "  make lint         - Verifie le style (ruff)"
	@echo "  make format       - Formate le code (ruff-format)"
	@echo "  make quality      - Lance pre-commit sur tout le depot"
	@echo "  make ci-local     - Reproduit localement le gate qualite principal"
	@echo "  make build-local  - Build image Docker et charge dans Minikube"
	@echo "  make deploy       - Deploie les manifestes Kubernetes"
	@echo "  make demo         - One-command local : build + deploy + port-forward"
	@echo "  make up-local     - Alias de make demo"
	@echo "  make monitoring   - Affiche les commandes de port-forward"
	@echo "  make benchmark    - Lance un benchmark Locust"
	@echo "  make clean        - Nettoie caches et fichiers temporaires"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pre_commit install

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=90

test-fast:
	$(PYTHON) -m pytest -q tests/test_api.py tests/test_health.py tests/test_schemas.py tests/test_llm_service.py

lint:
	$(PYTHON) -m ruff check app/ tests/
	$(PYTHON) -m ruff format --check app/ tests/

format:
	$(PYTHON) -m ruff check --fix app/ tests/
	$(PYTHON) -m ruff format app/ tests/

quality:
	$(PYTHON) -m pre_commit run --all-files

ci-local: lint test

build-local:
	docker build -t mlops-api:latest .
	minikube image load mlops-api:latest

deploy:
	kubectl apply -k gitops/overlays/minikube

demo:
	bash scripts/demo.sh

up-local: demo

monitoring:
	@echo "API     : kubectl port-forward svc/mlops-api -n mlops 8000:80"
	@echo "Grafana : kubectl port-forward svc/grafana-service -n mlops 3000:3000"
	@echo "Prometheus : kubectl port-forward svc/prometheus-service -n mlops 9090:9090"
	@echo "Loki    : kubectl port-forward svc/loki-service -n mlops 3100:3100"

benchmark:
	locust -f tests/locustfile.py --host http://localhost:8000 --users 5 --spawn-rate 1 --run-time 1m --headless

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml
