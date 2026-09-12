from flask import Blueprint

from . import controller as user_controller

user_bp = Blueprint("users", __name__)

user_bp.add_url_rule("/", view_func=user_controller.add_user, methods=["POST"])
user_bp.add_url_rule("/", view_func=user_controller.fetch_users, methods=["GET"])
user_bp.add_url_rule(
    "/<int:user_id>", view_func=user_controller.fetch_user_by_id, methods=["GET"]
)
user_bp.add_url_rule(
    "/<int:user_id>", view_func=user_controller.update_user, methods=["PUT"]
)
user_bp.add_url_rule(
    "/<int:user_id>", view_func=user_controller.delete_user, methods=["DELETE"]
)
