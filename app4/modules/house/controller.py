import logging

from flask import jsonify

from . import store as house_store

logger = logging.getLogger(__name__)


def fetch_houses():
    houses = house_store.get_all()
    logger.info("Found %s houses", len(houses), extra={"house.count": len(houses)})
    return jsonify(houses)


def fetch_house_by_id(house_id):
    house = house_store.get_by_id(house_id)
    if not house:
        # (body, status) tuple. server_span reads the 404 from it and sets
        # http.response.status_code. Span status is left unset for 4xx.
        logger.warning(
            "Could not find house with id %s", house_id, extra={"house.id": house_id}
        )
        return jsonify({"error": "house not found"}), 404
    logger.info("Found house %s", house_id, extra={"house.id": house_id})
    return jsonify(house)
