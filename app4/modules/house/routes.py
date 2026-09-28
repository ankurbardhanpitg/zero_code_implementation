"""House routes.

Each view is wrapped with server_span() at registration time. That is the
same wrap as @server_span on a function defined in this file; it is applied
by hand here because the view callables live in controller.py.

The string passed to server_span is the http.route attribute and the span
name suffix. It includes the blueprint prefix, because the decorator does
not see how the blueprint is mounted in app.py.

  GET /houses
      server span "GET /houses"
        └── houses.list          (store.get_all)
              └── houses.read

  GET /houses/<int:house_id>
      server span "GET /houses/<int:house_id>"
        └── houses.get_by_id     (store.get_by_id)
              └── houses.read
"""

from flask import Blueprint

from tracing import server_span

from . import controller as house_controller

house_bp = Blueprint("houses", __name__)

house_bp.add_url_rule(
    "/",
    view_func=server_span("/houses")(house_controller.fetch_houses),
    methods=["GET"],
    strict_slashes=False,
)
house_bp.add_url_rule(
    "/<int:house_id>",
    view_func=server_span("/houses/<int:house_id>")(house_controller.fetch_house_by_id),
    methods=["GET"],
)
