from datetime import datetime, timezone
from pathlib import Path
import json
import sys

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "houses.json"

SEED_HOUSES = [
    {"address": "12 MG Road, Bengaluru", "owner": "Aarav Sharma"},
    {"address": "88 Linking Road, Mumbai", "owner": "Priya Patel"},
    {"address": "5 Connaught Place, New Delhi", "owner": "Rohan Mehta"},
    {"address": "21 Anna Salai, Chennai", "owner": "Ananya Singh"},
    {"address": "17 Banjara Hills, Hyderabad", "owner": "Vikram Reddy"},
    {"address": "9 FC Road, Pune", "owner": "Neha Gupta"},
    {"address": "3 Marine Drive, Kochi", "owner": "Arjun Nair"},
    {"address": "64 Residency Road, Bengaluru", "owner": "Sneha Iyer"},
    {"address": "11 Law Garden, Ahmedabad", "owner": "Karan Joshi"},
    {"address": "2 Salt Lake, Kolkata", "owner": "Meera Das"},
]


def seed():
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    houses = [
        {
            "id": index,
            "address": house["address"],
            "owner": house["owner"],
            "createdAt": created_at,
        }
        for index, house in enumerate(SEED_HOUSES, start=1)
    ]

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(houses, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(houses)} houses to {DB_PATH}")


if __name__ == "__main__":
    try:
        seed()
    except OSError as error:
        print(f"Failed to seed houses: {error}", file=sys.stderr)
        sys.exit(1)
