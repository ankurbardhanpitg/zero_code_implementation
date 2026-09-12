# Flask User API (app3)

A small Flask user API. Users are stored in `data/users.json`. There is no OpenTelemetry instrumentation in this app.

## Prerequisites

- Python 3.12 or later
- `pip`

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

## Run the API

With the virtual environment still active:

```bash
python app.py
```

Without activating the venv, you can also start it with:

**PowerShell / Command Prompt:**

```powershell
.\.venv\Scripts\python.exe app.py
```

**bash / macOS / Linux:**

```bash
.venv/bin/python app.py
```

The server listens on [http://localhost:5000](http://localhost:5000). Keep this terminal running while you call the APIs.

Open [http://localhost:5000](http://localhost:5000) in a browser to confirm it is up. You should see a JSON health response with the endpoint list.

### Optional: use a different port

**PowerShell:**

```powershell
$env:PORT=5001; python app.py
```

**bash / macOS / Linux:**

```bash
PORT=5001 python app.py
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

Press `Ctrl+C` in the terminal where `python app.py` is running.

To leave the virtual environment:

```bash
deactivate
```
