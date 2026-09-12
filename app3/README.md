# Flask User API (app3)

A small Flask user API with **zero-code OpenTelemetry instrumentation**. Traces, metrics, and logs are exported to the local collector, then viewed in Grafana (Tempo, Prometheus, Loki).

The Flask source under `app.py` and `modules/` is unchanged. Instrumentation is loaded by `start.py` before the app starts.

## Prerequisites

- Python 3.12 or later
- `pip`
- Docker Desktop (for the observability stack)

## Setup

All commands below assume you are in the `app3` folder.

```bash
cd app3
```

### 1. Create the virtual environment

If `.venv` does not already exist:

```bash
python -m venv .venv
```

### 2. Activate the virtual environment

**PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this once in that terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Command Prompt:**

```bat
.venv\Scripts\activate.bat
```

**bash / macOS / Linux:**

```bash
source .venv/bin/activate
```

After activation, the prompt should show `(.venv)`.

### 3. Install dependencies

```bash
pip install -r requirements.txt
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

Grafana is on port **3001** so it does not clash with the Node APIs on port 3000. Anonymous admin access is enabled.

## 2. Start the API (instrumented)

From the `app3` folder, with the virtual environment active:

```bash
python start.py
```

`python start.py` loads `otel.env`, starts the OpenTelemetry SDK, then runs `app.py`. Application files under `app.py` and `modules/` are not modified.

The server listens on [http://localhost:5000](http://localhost:5000).

Keep this terminal running while you seed data or send traffic.

To run **without** instrumentation:

```bash
python app.py
```

Without activating the venv, you can also start it with:

**PowerShell / Command Prompt:**

```powershell
.\.venv\Scripts\python.exe start.py
```

**bash / macOS / Linux:**

```bash
.venv/bin/python start.py
```

### Optional: use a different port

**PowerShell:**

```powershell
$env:PORT=5001; python start.py
```

**bash / macOS / Linux:**

```bash
PORT=5001 python start.py
```

## 3. Seed users

In a second terminal, from the `app3` folder (venv active):

```bash
python scripts/seed_users.py
```

This writes 10 sample users with numeric ids `1` through `10` to `data/users.json`.

## 4. Generate continuous traffic

With the API still running, start the traffic script:

```bash
python scripts/traffic_users.py
```

The script repeatedly:

1. Calls `GET /users`
2. Calls `GET /users/<id>` for each user from that list

It keeps sending requests until you stop it.

### Stop the script

Press `Ctrl+C` in the traffic terminal. It prints a short summary of total, successful, and failed requests.

### Optional settings

| Variable       | Default                   | Description                          |
| -------------- | ------------------------- | ------------------------------------ |
| `BASE_URL`     | `http://localhost:5000`   | API base URL                         |
| `INTERVAL_MS`  | `500`                     | Delay between request loops, in ms   |

**PowerShell:**

```powershell
$env:INTERVAL_MS=200; python scripts/traffic_users.py
$env:BASE_URL="http://localhost:5000"; $env:INTERVAL_MS=200; python scripts/traffic_users.py
```

**bash / macOS / Linux:**

```bash
INTERVAL_MS=200 python scripts/traffic_users.py
BASE_URL=http://localhost:5000 INTERVAL_MS=200 python scripts/traffic_users.py
```

## 5. Observe performance in Grafana

Open [http://localhost:3001](http://localhost:3001).

1. Open the provisioned dashboard **OpenTelemetry services** (folder **OpenTelemetry**).
2. Use the **Service** dropdown at the top to pick an app. It is filled from `OTEL_SERVICE_NAME` on every app that exports traces to this collector (this API is `zero-code-python`). **Route** further filters RED metrics for that service.
3. After traffic is flowing you should see request rate, error rate, latency, recent **Tempo** traces, and **Loki** logs for the selected service. **Request rate by service** always shows every app so new services appear as soon as they send traces.
4. Dashboard links **Explore traces** and **Explore logs** open Tempo / Loki with the same service filter. Click a Trace ID in the traces table (or an exemplar on a metrics graph) to open the waterfall. Log lines that include a `trace_id` can jump to Tempo.

The Node.js event-loop panels stay empty for this app; RED metrics, traces, and logs still apply. Point additional apps at `http://localhost:4318` with a unique `OTEL_SERVICE_NAME`. They show up in the Service dropdown without changing Grafana.

### What each backend stores

| Signal  | Path | Backend |
| ------- | ---- | ------- |
| Traces  | Flask / WSGI auto-instrumentation → Collector → Tempo | request timing, routes, status |
| Metrics | OTLP HTTP metrics + spanmetrics derived from traces → Prometheus | RED (rate, errors, duration) |
| Logs    | OTLP logs → Collector → Loki | log records from the instrumented `logging` module |

`print()` is **not** auto-captured. Werkzeug request logs go through stdlib `logging`, so they are exported. Performance is observed from **traces and metrics**.

## How zero-code instrumentation works

No OpenTelemetry calls were added to `app.py` or the user module. `python start.py` is equivalent to:

1. Load `otel.env` (without overwriting variables already set in the shell)
2. Import `otel_register.py`, which starts the OpenTelemetry distro and auto-instrumentations
3. Run `app.py`

`otel.env` points the SDK at `http://localhost:4318` (the collector). Enabled libraries: `flask`, `wsgi`, `logging`, `exceptions`.

Override any value in `otel.env` by setting a real environment variable first; `start.py` does not overwrite variables that are already set.

You can also use the official agent CLI after exporting the same variables:

```bash
opentelemetry-instrument python app.py
```

## API endpoints

| Method   | Path           | Description                          |
| -------- | -------------- | ------------------------------------ |
| `GET`    | `/`            | Health / endpoint list               |
| `POST`   | `/users`       | Create a user                        |
| `GET`    | `/users`       | List all users                       |
| `GET`    | `/users/<id>`  | Get one user                         |
| `PUT`    | `/users/<id>`  | Update a user (`name` and/or `email`) |
| `DELETE` | `/users/<id>`  | Delete a user                        |

Users are persisted in `data/users.json`.

### Create a user

```bash
curl -X POST http://localhost:5000/users -H "Content-Type: application/json" -d "{\"name\":\"Test User\",\"email\":\"test@example.com\"}"
```

**PowerShell:**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:5000/users -ContentType "application/json" -Body '{"name":"Test User","email":"test@example.com"}'
```

### List all users

```bash
curl http://localhost:5000/users
```

### Get a user by id

```bash
curl http://localhost:5000/users/1
```

### Update a user

```bash
curl -X PUT http://localhost:5000/users/1 -H "Content-Type: application/json" -d "{\"name\":\"Updated User\"}"
```

### Delete a user

```bash
curl -X DELETE http://localhost:5000/users/1
```

## Stop the API

Press `Ctrl+C` in the terminal where `python start.py` is running.

To leave the virtual environment:

```bash
deactivate
```

## Stop the stack

From the `compose` folder:

```bash
docker compose down
```
