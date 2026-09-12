"""Start the Flask API with zero-code OpenTelemetry instrumentation.

Application files under app.py and modules/ are not modified.
Equivalent to the Node apps:

    node --env-file=otel.env --require ./otel-register.js index.js
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs without overwriting variables that are already set."""
    if not path.is_file():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_env_file(ROOT / "otel.env")

# Patch Flask/WSGI before the application is imported.
import otel_register  # noqa: E402, F401
from app import PORT, app  # noqa: E402

# Keep the debugger, but skip Werkzeug's reloader so the SDK is not started twice.
app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)
