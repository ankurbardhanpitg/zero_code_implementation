"""Flask entrypoint for the manually instrumented house API.

Trace setup for one request:

  1. init_tracing() installs the global TracerProvider before the house
     modules are imported. store.py calls trace.get_tracer() at import time,
     so the provider has to be in place first or that call receives the
     default proxy tracer.
  2. before_request extracts W3C trace context from the incoming headers and
     attaches it. server_span() does not take an explicit parent; it uses
     whatever context is current, so a traceparent on the request becomes
     the parent of the SERVER span.
  3. The view runs inside server_span()'s with-block. Child spans opened by
     store.py inherit that SERVER span the same way.
  4. teardown_request detaches the context, including when the view raises,
     so the next request on this worker thread does not keep this trace.
"""

import os

from flask import Flask, jsonify, request
from opentelemetry import context
from opentelemetry.propagate import extract

from tracing import init_tracing, server_span

init_tracing()

# Imported after init_tracing() on purpose; see the module docstring.
from modules.house.routes import house_bp  # noqa: E402

app = Flask(__name__)
app.register_blueprint(house_bp, url_prefix="/houses")

PORT = int(os.environ.get("PORT", 5002))

# context.attach() returns a token. It is stored on the WSGI environ because
# before_request and teardown_request are separate functions and do not share
# a local variable. The view code never reads this key.
_TOKEN_ENV = "previous_ctx_token"


@app.before_request
def attach_context_with_trace_header():
    """Attach incoming trace context for the rest of this request.

    extract() understands the W3C traceparent / tracestate headers carried
    on request.headers. attach() pushes the resulting context onto the
    current thread's OTel context stack. With no traceparent, the extracted
    context is empty and the SERVER span starts a new trace.
    """

    token = context.attach(extract(request.headers))
    request.environ[_TOKEN_ENV] = token


@app.teardown_request
def restore_context_on_teardown(err):
    """Detach the context pushed in before_request.

    Flask calls teardown_request after the response is produced and also
    when an unhandled exception escapes the view. detach(token) pops back
    to the context that was current before attach().
    """

    token = request.environ.get(_TOKEN_ENV)
    if token is not None:
        context.detach(token)


@app.get("/")
@server_span("/")
def health():
    # Recorded as a SERVER span named "GET /". See tracing.server_span.
    return jsonify(
        {
            "message": "House API is running",
            "service": "manual-python",
            "endpoints": {
                "fetchHouses": "GET /houses",
                "fetchHouseById": "GET /houses/<id>",
            },
        }
    )


if __name__ == "__main__":
    # The debug reloader spawns a child process that imports this module again.
    # use_reloader=False keeps a single process and a single TracerProvider.
    app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)
