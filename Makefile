# -----------------------------------------------------------------------------
# Makefile - workflow local standardise (API-only)
# -----------------------------------------------------------------------------

.PHONY: help install install-optional dev test test-fast test-unit test-contract test-integration test-e2e test-pyramid lint format quality prepush ci-local build-local deploy monitoring benchmark demo up-local clean

PYTHON ?= python

help:
	@echo "Commandes disponibles :"
	@echo "  make install      - Installe dependances + hooks pre-commit et pre-push"
	@echo "  make install-optional - Installe les dependances optionnelles (dagger, locust, selenium)"
	@echo "  make dev          - Lance l'API en mode developpement"
	@echo "  make test         - Lance tous les tests avec couverture"
	@echo "  make test-fast    - Lance un sous-ensemble de tests rapides"
	@echo "  make test-unit    - Lance les tests unitaires par couche"
	@echo "  make test-contract - Lance les tests de contrats/adapters"
	@echo "  make test-integration - Lance les tests d'integration applicative"
	@echo "  make test-e2e     - Lance le scenario E2E minimal API-only"
	@echo "  make test-pyramid - Lance la pyramide complete (unit -> contract -> integration -> e2e)"
	@echo "  make lint         - Verifie le style (ruff)"
	@echo "  make format       - Formate le code (ruff-format)"
	@echo "  make quality      - Lance pre-commit sur tout le depot"
	@echo "  make prepush      - Lance les checks du stage pre-push"
	@echo "  make ci-local     - Reproduit localement le gate complet (prepush + tests)"
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
	$(PYTHON) -m pre_commit install --hook-type pre-commit
	$(PYTHON) -m pre_commit install --hook-type pre-push

install-optional:
	$(PYTHON) -m pip install -r requirements-optional.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=90

test-fast:
	$(PYTHON) -m pytest -q tests/test_api.py tests/test_health.py tests/test_schemas.py tests/test_llm_service.py

test-unit:
	$(PYTHON) -m pytest -q tests/test_domain_contracts.py tests/test_application_use_cases.py tests/test_provider_resolution.py tests/test_prompt_and_provider_registry.py tests/test_llm_policies.py tests/test_architecture_boundaries.py

test-contract:
	$(PYTHON) -m pytest -q tests/test_llm_factory.py tests/test_llm_providers_and_observability.py tests/test_observability_gateway_adapter.py

test-integration:
	$(PYTHON) -m pytest -q tests/test_api.py tests/test_health.py tests/test_infrastructure_composition.py tests/test_llm_service.py tests/integration/test_pedantix_solver.py

test-e2e:
	$(PYTHON) -m pytest -q tests/e2e/

test-pyramid: test-unit test-contract test-integration test-e2e

lint:
	$(PYTHON) -m ruff check app/ tests/
	$(PYTHON) -m ruff format --check app/ tests/

format:
	$(PYTHON) -m ruff check --fix app/ tests/
	$(PYTHON) -m ruff format app/ tests/

quality:
	$(PYTHON) -m pre_commit run --all-files

prepush:
	$(PYTHON) -m pre_commit run --hook-stage pre-push --all-files

ci-local: prepush test

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
