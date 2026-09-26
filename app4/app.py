import os

from flask import Flask, jsonify, request
from opentelemetry import context
from opentelemetry.propagate import extract

from tracing import init_tracing, server_span

init_tracing()

from modules.house.routes import house_bp  # noqa: E402

app = Flask(__name__)
app.register_blueprint(house_bp, url_prefix="/houses")

PORT = int(os.environ.get("PORT", 5002))
_TOKEN_ENV = "previous_ctx_token"


@app.before_request
def attach_context_with_trace_header():
    token = context.attach(extract(request.headers))
    request.environ[_TOKEN_ENV] = token


@app.teardown_request
def restore_context_on_teardown(err):
    token = request.environ.get(_TOKEN_ENV)
    if token is not None:
        context.detach(token)


@app.get("/")
@server_span("/")
def health():
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
    app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)
