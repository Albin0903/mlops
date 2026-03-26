# Observabilite et monitoring

Le projet implemente une stack d'observabilite pour surveiller la performance et le cout des appels LLM.

## Metriques Prometheus et Grafana

FastAPI expose des metriques au format Prometheus.
- Dashboard Grafana : Taux de requetes, latence P95, taux d'erreur par modele.
- Custom Metrics : `llm_tokens_total`, `llm_latency_seconds`.

## Tracing LLM avec Langfuse

Suivi des interactions pour le debogage et la maitrise des couts :
- Traces : Historique des requetes, du prompt a la reponse.
- Metadata : Cout par appel et nombre de tokens.
- Debugging : Visualisation des prompts systeme.

## Accès local

- Grafana : `http://localhost:3000` (admin / admin).
- Prometheus : `http://localhost:8000/metrics`.
