# Flask House API (app4)

A small Flask house API with **manual OpenTelemetry tracing and metrics**. Nothing is auto-instrumented. The app creates the tracer and every span itself, using the same pipeline shape as `trace_solution` (`Resource`, `TracerProvider`, `BatchSpanProcessor`), and exports spans with OTLP HTTP to the local collector. Metrics use a separate `MeterProvider` in `metrics.py` and export to the same collector.

`GET /houses` and `GET /houses/<id>` each open a server span. The store opens child spans under that request.

## Prerequisites

- Python 3.12 or later
- `pip`
- Docker Desktop (for the observability stack)

## Setup

All commands below assume you are in the `app4` folder.

```bash
cd app4
```

### 1. Create the virtual environment

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 1. Start the observability stack

From the `compose` folder:

```bash
docker compose up --detach
```

Grafana is at [http://localhost:3001](http://localhost:3001). The collector receives OTLP HTTP on `localhost:4318`.

## 2. Start the API

From the `app4` folder, with the virtual environment active:

```bash
python app.py
```

`app.py` calls `init_tracing()` and `init_metrics()` before serving requests. There is no `start.py` and no Flask auto-instrumentation.

The server listens on [http://localhost:5002](http://localhost:5002).

Without activating the venv:

**PowerShell / Command Prompt:**

```powershell
.\.venv\Scripts\python.exe app.py
```

**bash / macOS / Linux:**

```bash
.venv/bin/python app.py
```

### Optional: use a different port or collector

**PowerShell:**

```powershell
$env:PORT=5003; python app.py
$env:OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"; python app.py
```

**bash / macOS / Linux:**

```bash
PORT=5003 python app.py
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python app.py
```

## 3. Seed houses

`data/houses.json` already contains 10 houses. To rewrite them:

```bash
python scripts/seed_houses.py
```

## 4. Generate continuous traffic

With the API running:

```bash
python scripts/traffic_houses.py
```

The script repeatedly calls `GET /houses`, `GET /houses/<id>` for each house, and `GET /houses/999` (a 404). Stop it with `Ctrl+C`.

| Variable | Default | Description |
| --- | --- | --- |
| `BASE_URL` | `http://localhost:5002` | API base URL |
| `INTERVAL_MS` | `500` | Delay between request loops, in ms |

## 5. Dashboards

Open [http://localhost:3001](http://localhost:3001). Two dashboards in the **OpenTelemetry** folder are for this app. Both are separate from **OpenTelemetry services**.

**Manual instrumentation — houses** is the trace view. Every panel is fixed to `service.name` = `manual-python`. Use **Route** for the HTTP server spans and **Manual span** for the child spans written in `store.py`.

After traffic is flowing you should see:

| Span | Kind | Where it is created |
| --- | --- | --- |
| `GET /houses` | server | `server_span` on the list route |
| `houses.list` | internal | `store.get_all` |
| `houses.read` | internal | `store._read_houses` |
| `GET /houses/<int:house_id>` | server | `server_span` on the get-by-id route |
| `houses.get_by_id` | internal | `store.get_by_id` |

Click a trace in the Tempo panels to open the waterfall. `house.id` and `house.found` are attributes on `houses.get_by_id`.

**Manual metrics — houses** reads the instruments from `metrics.py`: `traffic_volume`, `error_rate`, `http.server.request.duration`, CPU, and memory. Use **Route** there to filter the HTTP panels. Process panels cover the whole process.

The request-rate panels on the trace dashboard are built by the collector from spans. The metrics dashboard uses the counters and histogram recorded in `app.py`. There is no log pipeline, so neither dashboard has a Loki panel.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health / endpoint list |
| `GET` | `/houses` | List all houses |
| `GET` | `/houses/<id>` | Get one house |

### List houses

```bash
curl http://localhost:5002/houses
```

### Get a house by id

```bash
curl http://localhost:5002/houses/1
```

## Stop the API

Press `Ctrl+C` in the terminal where `python app.py` is running.

To leave the virtual environment:

```bash
deactivate
```
