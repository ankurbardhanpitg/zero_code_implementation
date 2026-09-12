from datetime import datetime, timezone
from pathlib import Path
import json
import sys

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.json"

SEED_USERS = [
    {"name": "Aarav Sharma", "email": "aarav.sharma@example.com"},
    {"name": "Priya Patel", "email": "priya.patel@example.com"},
    {"name": "Rohan Mehta", "email": "rohan.mehta@example.com"},
    {"name": "Ananya Singh", "email": "ananya.singh@example.com"},
    {"name": "Vikram Reddy", "email": "vikram.reddy@example.com"},
    {"name": "Neha Gupta", "email": "neha.gupta@example.com"},
    {"name": "Arjun Nair", "email": "arjun.nair@example.com"},
    {"name": "Sneha Iyer", "email": "sneha.iyer@example.com"},
    {"name": "Karan Joshi", "email": "karan.joshi@example.com"},
    {"name": "Meera Das", "email": "meera.das@example.com"},
]


def seed():
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    users = [
        {
            "id": index,
            "name": user["name"],
            "email": user["email"],
            "createdAt": created_at,
        }
        for index, user in enumerate(SEED_USERS, start=1)
    ]

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(users)} users to {DB_PATH}")


if __name__ == "__main__":
    try:
        seed()
    except OSError as error:
        print(f"Failed to seed users: {error}", file=sys.stderr)
        sys.exit(1)
