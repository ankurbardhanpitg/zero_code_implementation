# Kubernetes Observability Stack (Docker Desktop)

Deploys the same stack as `compose/` onto Docker Desktop Kubernetes:

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

From the repo root:

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
kubectl delete -k k8s
```

## Notes

- Runtime configs live under `k8s/config/` (copied from `compose/` so Kustomize can load them).
- If you change Compose configs, copy the updated files into `k8s/config/` again, then re-apply.
- Storage uses `emptyDir` (data is lost when pods restart). Fine for local study.
- Service names match Compose (`otel-collector`, `prometheus`, `loki`, `tempo`, `grafana`), so existing configs keep working.
