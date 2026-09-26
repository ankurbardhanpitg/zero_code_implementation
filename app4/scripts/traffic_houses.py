import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5002").rstrip("/")
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", "500"))

running = True
request_count = 0
success_count = 0
error_count = 0


def fetch_json(path):
    global request_count, success_count, error_count

    url = f"{BASE_URL}{path}"
    started_at = time.perf_counter()
    request_count += 1

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
            status = response.status
            ok = 200 <= status < 300
    except urllib.error.HTTPError as error:
        status = error.code
        ok = False
        body = None
        try:
            body = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            body = None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        error_count += 1
        print(f"[{request_count}] ERROR GET {path}: {error}", file=sys.stderr)
        return False, None

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if ok:
        success_count += 1
    else:
        error_count += 1

    print(f"[{request_count}] {status} GET {path} ({duration_ms}ms)")
    return ok, body


def send_traffic():
    print(f"Sending traffic to {BASE_URL} every {INTERVAL_MS}ms")
    print("Press Ctrl+C to stop\n")

    while running:
        ok, houses = fetch_json("/houses")

        if running and ok and isinstance(houses, list):
            for house in houses:
                if not running:
                    break
                house_id = house.get("id") if isinstance(house, dict) else None
                if house_id is None:
                    continue
                fetch_json(f"/houses/{house_id}")

        if running:
            fetch_json("/houses/999")

        if running:
            time.sleep(INTERVAL_MS / 1000)


def stop(*_args):
    global running
    if not running:
        return
    running = False
    print("\nStopping traffic script...")
    print(
        f"Done. requests={request_count} success={success_count} errors={error_count}"
    )


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    try:
        send_traffic()
    except KeyboardInterrupt:
        stop()
        sys.exit(0)
