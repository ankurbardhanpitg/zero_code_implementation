import json
from pathlib import Path

from opentelemetry import trace

from tracing import SERVICE_VERSION

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "houses.json"
tracer = trace.get_tracer("app4.house", SERVICE_VERSION)


def _read_houses():
    with tracer.start_as_current_span("houses.read") as span:
        try:
            houses = json.loads(DB_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            span.set_attribute("house.count", 0)
            return []
        span.set_attribute("house.count", len(houses))
        return houses


def _matches_id(house, house_id):
    return int(house["id"]) == int(house_id)


def get_all():
    with tracer.start_as_current_span("houses.list") as span:
        houses = _read_houses()
        span.set_attribute("house.count", len(houses))
        return houses


def get_by_id(house_id):
    with tracer.start_as_current_span("houses.get_by_id") as span:
        span.set_attribute("house.id", int(house_id))
        for house in _read_houses():
            if _matches_id(house, house_id):
                span.set_attribute("house.found", True)
                return house
        span.set_attribute("house.found", False)
        return None
