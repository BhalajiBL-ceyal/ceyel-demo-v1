"""
Startup script to auto-load sample data into the database on first run.
Run this once after starting the server:  python load_sample_data.py
"""

import json
import urllib.request
import sys
import time

API_BASE = "http://localhost:8000"
SAMPLE_FILE = "data/sample_events.json"


def wait_for_server(retries=10, delay=2):
    for i in range(retries):
        try:
            urllib.request.urlopen(f"{API_BASE}/api/mining/stats", timeout=5)
            return True
        except Exception:
            print(f"  Waiting for server... ({i+1}/{retries})")
            time.sleep(delay)
    return False


def load_sample_data():
    print("[RUNNING] Loading sample events into Ceyel...")

    if not wait_for_server():
        print("[ERROR] Server not reachable. Make sure run.bat is running first.")
        sys.exit(1)

    with open(SAMPLE_FILE, "r") as f:
        events = json.load(f)

    data = json.dumps(events).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/api/events/bulk",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"[OK] Ingested {result['ingested']} events ({result['failed']} failed).")

    # Commit initial blockchain block
    req2 = urllib.request.Request(
        f"{API_BASE}/api/blockchain/commit",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req2) as resp2:
        block = json.loads(resp2.read())
        print(f"[CHAIN] Genesis block committed: {block['block']['block_hash'][:16]}...")

    print("\n[SUCCESS] Sample data loaded! Open http://localhost:8000 to view the dashboard.")


if __name__ == "__main__":
    load_sample_data()
