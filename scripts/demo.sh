#!/usr/bin/env bash
set -euo pipefail

WITH_PORT_FORWARD=true
WITH_SMOKE=true

usage() {
  cat <<'USAGE'
Usage: scripts/demo.sh [options]

Options:
  --no-port-forward   Do not start kubectl port-forward processes.
  --no-smoke          Skip quick health smoke check.
  -h, --help          Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-port-forward)
      WITH_PORT_FORWARD=false
      ;;
    --no-smoke)
      WITH_SMOKE=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1"
    exit 1
  fi
}

require_cmd make
require_cmd docker
require_cmd kubectl
require_cmd minikube

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "info: ensure namespace mlops exists"
kubectl get namespace mlops >/dev/null 2>&1 || kubectl create namespace mlops >/dev/null

echo "info: build + load image in minikube"
make build-local

echo "info: deploy stack with kustomize overlay"
make deploy

echo "info: waiting for core deployments"
for dep in mlops-api prometheus grafana loki; do
  if kubectl -n mlops get deployment "$dep" >/dev/null 2>&1; then
    kubectl -n mlops rollout status "deployment/$dep" --timeout=180s
  fi
done

if [[ "$WITH_PORT_FORWARD" != "true" ]]; then
  echo "info: deployment complete"
  echo "info: run 'make monitoring' to show port-forward commands"
  exit 0
fi

PF_LOG_DIR="$(mktemp -d -t mlops-demo-XXXXXX)"
pids=()

cleanup() {
  if [[ ${#pids[@]} -gt 0 ]]; then
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
  fi
  if [[ -d "$PF_LOG_DIR" ]]; then
    rm -rf "$PF_LOG_DIR"
  fi
}

trap cleanup EXIT INT TERM

start_port_forward() {
  local service="$1"
  local local_port="$2"
  local remote_port="$3"

  kubectl -n mlops port-forward "svc/$service" "$local_port:$remote_port" >"$PF_LOG_DIR/$service.log" 2>&1 &
  pids+=("$!")
}

echo "info: starting port-forwards"
start_port_forward "mlops-api" "8000" "80"
start_port_forward "grafana-service" "3000" "3000"
start_port_forward "prometheus-service" "9090" "9090"
start_port_forward "loki-service" "3100" "3100"

sleep 3

echo "info: endpoints"
echo "- API:        http://127.0.0.1:8000/health/"
echo "- Grafana:    http://127.0.0.1:3000"
echo "- Prometheus: http://127.0.0.1:9090"
echo "- Loki:       http://127.0.0.1:3100"

if [[ "$WITH_SMOKE" == "true" ]] && command -v curl >/dev/null 2>&1; then
  echo "info: health smoke check"
  curl -fsS "http://127.0.0.1:8000/health/" | cat
fi

echo "info: demo running (Ctrl+C to stop and cleanup)"
wait
