# Zero Code Node

A small Express user API with **zero-code OpenTelemetry instrumentation**. Traces, metrics, and logs are exported to the local collector, then viewed in Grafana (Tempo, Prometheus, Loki).

The Express source under `index.js` and `modules/` is unchanged. Instrumentation is loaded with Node's `--require` hook before the app starts.

## Prerequisites

- Node.js 20.6 or later (`npm start` uses `--env-file`)
- npm
- Docker Desktop (for the observability stack)

## Setup

From the `app` folder:

```bash
npm install
```

## 1. Start the observability stack

From the `compose` folder:

```bash
docker compose up --detach
```

This starts:

| Service        | Host URL                    | Role                                      |
| -------------- | --------------------------- | ----------------------------------------- |
| OTel Collector | `localhost:4318` (OTLP HTTP) | Receives app telemetry                    |
| Prometheus     | [http://localhost:9090](http://localhost:9090) | Stores metrics                   |
| Loki           | [http://localhost:3100](http://localhost:3100) | Stores logs                      |
| Tempo          | [http://localhost:3200](http://localhost:3200) | Stores traces                    |
| Grafana        | [http://localhost:3001](http://localhost:3001) | Dashboards and Explore           |

Grafana is on port **3001** so it does not clash with the API on port 3000. Anonymous admin access is enabled.

## 2. Start the API (instrumented)

From the `app` folder, in another terminal:

```bash
npm start
```

`npm start` loads `otel.env`, starts the OpenTelemetry SDK, then preloads `http` so Express 5 (`node:http`) is patched. Application files under `index.js` and `modules/` are not modified.

The server listens on [http://localhost:3000](http://localhost:3000).

Keep this terminal running while you seed data or send traffic.

To run **without** instrumentation:

```bash
npm run start:plain
```

## 3. Seed users

In a second terminal, from the `app` folder:

```bash
npm run seed:users
```

This writes 10 sample users with numeric ids `1` through `10` to `data/users.json`.

## 4. Generate continuous traffic

With the API still running, start the traffic script:

```bash
npm run traffic:users
```

The script repeatedly:

1. Calls `GET /users`
2. Calls `GET /users/:id` for a random user from that list

It keeps sending requests until you stop it.

### Stop the script

Press `Ctrl+C` in the traffic terminal. It prints a short summary of total, successful, and failed requests.

### Optional settings

| Variable       | Default                   | Description                          |
| -------------- | ------------------------- | ------------------------------------ |
| `BASE_URL`     | `http://localhost:3000`   | API base URL                         |
| `INTERVAL_MS`  | `500`                     | Delay between request loops, in ms   |

**PowerShell:**

```powershell
$env:INTERVAL_MS=200; npm run traffic:users
$env:BASE_URL="http://localhost:3000"; $env:INTERVAL_MS=200; npm run traffic:users
```

**bash / macOS / Linux:**

```bash
INTERVAL_MS=200 npm run traffic:users
BASE_URL=http://localhost:3000 INTERVAL_MS=200 npm run traffic:users
```

## 5. Observe performance in Grafana

Open [http://localhost:3001](http://localhost:3001).

1. Open the provisioned dashboard **OpenTelemetry services** (folder **OpenTelemetry**).
2. Use the **Service** dropdown at the top to pick an app. It is filled from `OTEL_SERVICE_NAME` on every app that exports traces to this collector (this API is `zero-code-node`). **Route** further filters RED metrics for that service.
3. After traffic is flowing you should see request rate, error rate, latency, Node.js runtime, recent **Tempo** traces, and **Loki** logs for the selected service. **Request rate by service** always shows every app so new services appear as soon as they send traces.
4. Dashboard links **Explore traces** and **Explore logs** open Tempo / Loki with the same service filter. Click a Trace ID in the traces table (or an exemplar on a metrics graph) to open the waterfall. Log lines that include a `trace_id` can jump to Tempo.

Point additional apps at `http://localhost:4318` with a unique `OTEL_SERVICE_NAME`. They show up in the Service dropdown without changing Grafana.

### What each backend stores

| Signal  | Path | Backend |
| ------- | ---- | ------- |
| Traces  | Express / HTTP auto-instrumentation → Collector → Tempo | request timing, routes, status |
| Metrics | OTLP HTTP metrics + spanmetrics derived from traces → Prometheus | RED (rate, errors, duration) |
| Logs    | OTLP logs → Collector → Loki | log records from instrumented loggers |

`console.log` is **not** auto-captured. Loki stays empty unless the app uses a supported logger such as `pino` or `winston`. Performance is observed from **traces and metrics**.

## How zero-code instrumentation works

No OpenTelemetry calls were added to `index.js` or the user module. `npm start` is equivalent to:

```bash
node --env-file=otel.env --require ./otel-register.js index.js
```

`otel-register.js` starts `@opentelemetry/auto-instrumentations-node` and requires Node's `http` module so Express 5 is patched. `otel.env` points the SDK at `http://localhost:4318` (the collector). Enabled libraries: `http`, `express`, `router`, `runtime-node`.

Override any value in `otel.env` by setting a real environment variable first; Node does not overwrite variables that are already set.

## API endpoints

| Method   | Path          | Description        |
| -------- | ------------- | ------------------ |
| `GET`    | `/`           | Health / endpoint list |
| `POST`   | `/users`      | Create a user      |
| `GET`    | `/users`      | List all users     |
| `GET`    | `/users/:id`  | Get one user       |
| `DELETE` | `/users/:id`  | Delete a user      |

Create a user:

```bash
curl -X POST http://localhost:3000/users -H "Content-Type: application/json" -d "{\"name\":\"Test User\",\"email\":\"test@example.com\"}"
```

## Stop the stack

From the `compose` folder:

```bash
docker compose down
```
