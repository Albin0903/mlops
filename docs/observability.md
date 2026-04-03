# Observabilite et monitoring

Le projet implemente une stack d'observabilite pour surveiller la performance et le cout des appels LLM.

## Metriques Prometheus et Grafana

FastAPI expose des metriques au format Prometheus.
- Dashboard API : volume HTTP, codes statut, latence moyenne, request rate.
- Dashboard Quotas LLM : suivi RPM/RPD/TPD/TPM et budget restant par modele.
- Dashboard LLM avance : tokens in/out, latence moyenne par modele, cout cumule estime sur 24h.
- Custom metrics LLM : `llm_requests_total`, `llm_tokens_total`, `llm_latency_seconds`.

Le cout cumule est une estimation basee sur des tarifs USD par million de tokens
configures directement dans les requetes Grafana.

## Alerting Prometheus

Regles d'alerte actives :
- Latence P95 HTTP > 5s pendant 5 minutes.
- Taux d'erreur HTTP 5xx > 5% pendant 5 minutes.
- Quotas LLM > 80% (RPM/RPD/TPD pour Groq, RPM/RPD/TPM pour Gemini).

## Logs centralises (Loki + Promtail)

- Loki stocke les logs applicatifs et plateforme dans le namespace `mlops`.
- Promtail collecte les logs des pods Kubernetes et les pousse vers Loki.
- Grafana expose une datasource Loki et un panneau logs dans le dashboard quotas.

## Tracing LLM avec Langfuse

Suivi des interactions pour le debogage et la maitrise des couts :
- Traces : Historique des requetes, du prompt a la reponse.
- Metadata : Cout par appel et nombre de tokens.
- Debugging : Visualisation des prompts systeme.

## Accès local

- Grafana : `http://localhost:3000` (admin / admin).
- Prometheus UI : `http://localhost:9090`.
- Loki API : `http://localhost:3100`.

Port-forward utiles :
- `kubectl port-forward svc/grafana-service -n mlops 3000:3000`
- `kubectl port-forward svc/prometheus-service -n mlops 9090:9090`
- `kubectl port-forward svc/loki-service -n mlops 3100:3100`
