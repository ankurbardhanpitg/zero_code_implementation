"""Official zero-code SDK (traces, metrics, logs, auto-instrumentations).

Must be imported before Flask so WSGI/Flask are patched. Same role as
`otel-register.js` in the Node apps (`node --require ./otel-register.js`).
"""

from opentelemetry.instrumentation.auto_instrumentation import initialize

initialize()
