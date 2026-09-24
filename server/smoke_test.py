"""End-to-end smoke test for license_server.py - no external deps.
Spins the real HTTP server on a random port and exercises every endpoint.

The response helper intentionally returns dynamic JSON, so Pylint cannot infer
that its second tuple item is subscriptable.
"""
# pylint: disable=unsubscriptable-object
import hashlib
import hmac
import http.client
import json
import os
import sys
import tempfile
import threading
import time
from typing import Any

os.environ["PADDLE_WEBHOOK_SECRET"] = "test_secret_123"
os.environ["XTOBE_LICENSE_DB"] = os.path.join(tempfile.mkdtemp(), "licenses.json")
os.environ["PORT"] = "8899"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_server as srv

threading.Thread(target=srv.ThreadingHTTPServer(("127.0.0.1", 8899), srv.Handler).serve_forever, daemon=True).start()
time.sleep(0.3)


def req(method: str, path: str, body: Any = None, headers: Any = None) -> tuple[int, Any]:
    c = http.client.HTTPConnection("127.0.0.1", 8899, timeout=5)
    c.request(method, path, json.dumps(body) if body is not None else None,
              headers or {"Content-Type": "application/json"})
    r = c.getresponse()
    raw = r.read()
    return r.status, json.loads(raw) if raw else None


# 1) health
s, b = req("GET", "/health")
assert s == 200 and b["ok"], "health failed"
print("1. /health OK")

# 2) webhook with BAD signature must be rejected
s, b = req("POST", "/webhooks/paddle", {"event_type": "transaction.completed", "data": {}},
           {"Paddle-Signature": "ts=1;h1=bad"})
assert s == 401, f"bad sig accepted! {s}"
print("2. bad webhook signature rejected (401) OK")

# 3) webhook with VALID signature issues a license key
payload = json.dumps({
    "event_type": "transaction.completed",
    "data": {"id": "txn_01TEST", "customer": {"email": "buyer@example.com"}},
}).encode()
ts = str(int(time.time()))
h1 = hmac.new(b"test_secret_123", f"{ts}:".encode() + payload, hashlib.sha256).hexdigest()
c = http.client.HTTPConnection("127.0.0.1", 8899, timeout=5)
c.request("POST", "/webhooks/paddle", payload,
          {"Content-Type": "application/json", "Paddle-Signature": f"ts={ts};h1={h1}"})
r = c.getresponse()
resp = json.loads(r.read())
assert r.status == 200 and resp["license_issued"], f"webhook failed: {r.status} {resp}"
key = list(srv._load_db()["licenses"])[0]
print(f"3. valid webhook -> license issued: {key} OK")

# 4) license heartbeat with the issued key (simulates the Rust client)
s, b = req("POST", "/api/license-check",
           {"license_key": key, "machine_id": "machine-abc", "version": "2.0.0"})
assert s == 200 and b["valid"] and b["tier"] == "lifetime", f"heartbeat failed: {b}"
print(f"4. /api/license-check heartbeat valid, tier={b['tier']} OK")

# 5) unknown key rejected
s, b = req("POST", "/api/license-check", {"license_key": "XTOBE-FAKE", "machine_id": "m"})
assert not b["valid"], "fake key accepted!"
print("5. unknown key rejected OK")

# 6) updater feed: current==latest -> 204, older -> 200 payload or 204 w/o artifacts
c = http.client.HTTPConnection("127.0.0.1", 8899, timeout=5)
c.request("GET", "/api/updates/windows/x86_64/2.0.0")
assert c.getresponse().status == 204, "latest version should return 204"
print("6. updater feed 204 (already latest) OK")

print("\nALL SERVER SMOKE TESTS PASSED")
