# Kubernetes Observability Stack (Docker Desktop)

Self-contained under `k8s/` (no dependency on `compose/` files at apply time).

Deploys:

- OpenTelemetry Collector
- Prometheus
- Loki
- Tempo
- Grafana

## Prerequisites

1. Docker Desktop → **Settings** → **Kubernetes** → **Enable Kubernetes**
2. Wait until Kubernetes is running
3. Stop the Compose observability stack if it is running (avoids port conflicts on `4317`, `4318`, `9090`, `3001`):

```powershell
docker compose -f compose/compose.yaml down
```

## Deploy

From the `k8s` folder:

```powershell
.\apply.ps1
```

Or from the repo root:

```powershell
kubectl apply -k k8s
```

Watch pods:

```powershell
kubectl get pods -n observability -w
```

## Access (Docker Desktop LoadBalancer)

| Service | URL |
|---|---|
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| OTLP gRPC | `localhost:4317` |
| OTLP HTTP | http://localhost:4318 |

Grafana anonymous admin is enabled (same as Compose).

## Point apps at the collector

From your host / local Node apps:

```text
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

From another pod in the cluster:

```text
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4318
```

## Useful commands

```powershell
kubectl get all -n observability
kubectl logs -n observability deploy/otel-collector -f
kubectl logs -n observability deploy/grafana -f
```

## Tear down

```powershell
.\delete.ps1
```

Or:

```powershell
kubectl delete -k k8s
```

## Notes

- All runtime configs live under `k8s/config/` (collector, prometheus, loki, tempo, grafana).
- Edit files only inside `k8s/` for the Kubernetes stack; Compose keeps its own configs under `compose/`.
- Storage uses `emptyDir` (data is lost when pods restart). Fine for local study.
- Service names match Compose (`otel-collector`, `prometheus`, `loki`, `tempo`, `grafana`).
