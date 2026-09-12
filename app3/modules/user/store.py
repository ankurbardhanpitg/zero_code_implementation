import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "users.json"


def _read_users():
    try:
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _write_users([])
        return []


def _write_users(users):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")


def _next_id(users):
    if not users:
        return 1
    return max(int(user.get("id") or 0) for user in users) + 1


def _matches_id(user, user_id):
    return int(user["id"]) == int(user_id)


def get_all():
    return _read_users()


def get_by_id(user_id):
    for user in _read_users():
        if _matches_id(user, user_id):
            return user
    return None


def create(user_data):
    users = _read_users()
    user = {
        "id": _next_id(users),
        "name": user_data["name"],
        "email": user_data["email"],
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    users.append(user)
    _write_users(users)
    return user


def update(user_id, user_data):
    users = _read_users()
    for index, user in enumerate(users):
        if not _matches_id(user, user_id):
            continue

        updated_user = dict(user)
        if "name" in user_data and user_data["name"] is not None:
            updated_user["name"] = user_data["name"]
        if "email" in user_data and user_data["email"] is not None:
            updated_user["email"] = user_data["email"]
        updated_user["updatedAt"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        users[index] = updated_user
        _write_users(users)
        return updated_user

    return None


def remove(user_id):
    users = _read_users()
    for index, user in enumerate(users):
        if _matches_id(user, user_id):
            deleted_user = users.pop(index)
            _write_users(users)
            return deleted_user
    return None
