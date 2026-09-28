"""Flask entrypoint for the manually instrumented house API.

Trace setup for one request:

  1. init_tracing() installs the global TracerProvider before the house
     modules are imported. store.py calls trace.get_tracer() at import time,
     so the provider has to be in place first or that call receives the
     default proxy tracer.
  2. init_metrics() installs the global MeterProvider. It does not change
     the tracer. The HTTP instruments it returns are recorded by the
     request hooks below.
  3. before_request extracts W3C trace context from the incoming headers and
     attaches it, then counts the request. server_span() does not take an
     explicit parent; it uses whatever context is current, so a traceparent
     on the request becomes the parent of the SERVER span.
  4. The view runs inside server_span()'s with-block. Child spans opened by
     store.py inherit that SERVER span the same way.
  5. after_request records latency and, for status 400 and above, an error.
     teardown_request records a 500 when the view raises before after_request
     runs, then detaches the trace context so the next request on this
     worker thread does not keep this trace.
"""

import os
import time

from flask import Flask, Response, jsonify, request
from opentelemetry import context
from opentelemetry.propagate import extract

from metrics import init_metrics
from tracing import init_tracing, server_span

init_tracing()
request_instruments = init_metrics()

# Imported after init_tracing() on purpose; see the module docstring.
from modules.house.routes import house_bp  # noqa: E402

app = Flask(__name__)
app.register_blueprint(house_bp, url_prefix="/houses")

PORT = int(os.environ.get("PORT", 5002))

# context.attach() returns a token. It is stored on the WSGI environ because
# before_request and teardown_request are separate functions and do not share
# a local variable. The view code never reads this key.
_TOKEN_ENV = "previous_ctx_token"
_START_ENV = "request_start_ns"
_METRICS_RECORDED_ENV = "http_metrics_recorded"


def _http_route() -> str:
    """Route template for metric attributes.

    url_rule.rule is the matched pattern, including the blueprint prefix,
    for example "/houses/<int:house_id>". An unmatched path has no rule,
    so the concrete path is used instead. A trailing slash is removed so
    the list route is "/houses", the same value server_span records.
    """

    rule = request.url_rule
    path = request.path if rule is None else rule.rule
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def _record_http_metrics(status_code: int) -> None:
    """Record latency once, and an error count when the status is a failure.

    after_request and teardown_request can both run for one request. The
    environ flag makes the second call a no-op.
    """

    started = request.environ.get(_START_ENV)
    if started is None or request.environ.get(_METRICS_RECORDED_ENV):
        return
    request.environ[_METRICS_RECORDED_ENV] = True

    route = _http_route()
    request_instruments["request_latency"].record(
        amount=(time.time_ns() - started) / 1_000_000_000,
        attributes={
            "http.request.method": request.method,
            "http.route": route,
            "http.response.status_code": status_code,
        },
    )
    if status_code >= 400:
        request_instruments["error_rate"].add(
            1,
            attributes={
                "http.route": route,
                "http.response.status_code": status_code,
            },
        )


@app.before_request
def attach_context_with_trace_header():
    """Attach incoming trace context and count this request.

    extract() understands the W3C traceparent / tracestate headers carried
    on request.headers. attach() pushes the resulting context onto the
    current thread's OTel context stack. With no traceparent, the extracted
    context is empty and the SERVER span starts a new trace.

    The start timestamp is stored on the environ so after_request can turn
    it into a duration. traffic_volume counts every request that reaches
    this hook, including ones that later fail.
    """

    token = context.attach(extract(request.headers))
    request.environ[_TOKEN_ENV] = token
    request.environ[_START_ENV] = time.time_ns()
    request_instruments["traffic_volume"].add(
        1, attributes={"http.route": _http_route()}
    )


@app.after_request
def record_http_metrics(response: Response) -> Response:
    """Record latency from the response Flask is about to send.

    Flask has already turned the view return value into a Response, so
    status_code is the status the client receives. This hook does not run
    when an unhandled exception escapes the view; teardown_request covers
    that case.
    """

    _record_http_metrics(response.status_code)
    return response


@app.teardown_request
def restore_context_on_teardown(err):
    """Record a 500 if the view raised, then detach trace context.

    Flask calls teardown_request after the response is produced and also
    when an unhandled exception escapes the view. When err is set and
    after_request did not run, the status recorded on the histogram is 500.
    detach(token) pops back to the context that was current before attach().
    """

    if err is not None:
        _record_http_metrics(500)
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
