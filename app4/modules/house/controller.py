from flask import jsonify

from . import store as house_store


def fetch_houses():
    return jsonify(house_store.get_all())


def fetch_house_by_id(house_id):
    house = house_store.get_by_id(house_id)
    if not house:
        # (body, status) tuple. server_span reads the 404 from it and sets
        # http.response.status_code. Span status is left unset for 4xx.
        return jsonify({"error": "house not found"}), 404
    return jsonify(house)
