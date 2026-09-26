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
