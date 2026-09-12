from flask import jsonify, request

from . import store as user_store


def add_user():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    email = body.get("email")

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    user = user_store.create({"name": name, "email": email})
    return jsonify(user), 201


def fetch_users():
    return jsonify(user_store.get_all())


def fetch_user_by_id(user_id):
    user = user_store.get_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


def update_user(user_id):
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    email = body.get("email")

    if name is None and email is None:
        return jsonify({"error": "name or email is required"}), 400

    user = user_store.update(user_id, {"name": name, "email": email})
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


def delete_user(user_id):
    deleted_user = user_store.remove(user_id)
    if not deleted_user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"message": "user deleted", "user": deleted_user})
