"""
Xtobe License + Update Server (stdlib only - no pip deps)
----------------------------------------------------------
Run behind HTTPS on xtobe.app (Caddy/Nginx reverse proxy).

  POST /webhooks/paddle                    Paddle webhook (HMAC verified) -> issue/revoke key
  POST /api/license-check                  Heartbeat from the installed app
  GET  /api/updates/<target>/<arch>/<ver>  Tauri auto-updater feed
  GET  /health                             liveness

Env: PADDLE_WEBHOOK_SECRET, XTOBE_LICENSE_DB, XTOBE_UPDATE_DIR, XTOBE_UPDATE_BASEURL
"""
import smtplib
from email.message import EmailMessage
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

STARTED_AT = time.time()
WEBHOOK_SECRET = os.environ.get("PADDLE_WEBHOOK_SECRET", "pdl_ntfset_replace_me")

WEBHOOK_SECRET = os.environ.get("PADDLE_WEBHOOK_SECRET", "pdl_ntfset_replace_me")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "Xtobe <licenses@xtobe.app>")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") not in ("0", "false", "False")
SMTP_TIMEOUT = int(os.environ.get("SMTP_TIMEOUT", "15"))


def send_email(to: str, subject: str, body: str) -> bool:
    """Best-effort SMTP delivery; webhook persistence remains successful."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("SMTP not configured; email skipped", flush=True)
        return False
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = SMTP_FROM, to, subject
    message.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)
        return True
    except Exception as exc:
        print(f"email delivery failed for {to}: {exc}", flush=True)
        return False
DB_PATH = os.environ.get("XTOBE_LICENSE_DB", "licenses.json")
UPDATE_DIR = os.environ.get("XTOBE_UPDATE_DIR", "./releases")
UPDATE_BASE = os.environ.get("XTOBE_UPDATE_BASEURL", "https://xtobe.app/dl").rstrip("/")
LATEST_VERSION = "2.0.0"
MAX_MACHINES = 3


def _load_db():
    if not os.path.exists(DB_PATH):
        return {"licenses": {}}
    return json.load(open(DB_PATH, encoding="utf-8"))


def _save_db(db):
    tmp = DB_PATH + ".tmp"
    json.dump(db, open(tmp, "w", encoding="utf-8"), indent=2)
    os.replace(tmp, DB_PATH)


def issue_license(email: str, paddle_txn: str) -> str:
    key = "XTOBE-" + "-".join(secrets.token_hex(2).upper() for _ in range(4))
    db = _load_db()
    db["licenses"][key] = {
        "email": email,
        "paddle_txn": paddle_txn,
        "key": key,
        "product": "xtobe-final-guardian",
        "tier": "lifetime",
        "issued": datetime.now(timezone.utc).isoformat(),
        "machines": [],
        "revoked": False,
    }
    _save_db(db)
    send_email(email, "Your Xtobe license key",
               "Thank you for purchasing Xtobe Final Guardian.\n\n"
               f"Your license key is: {key}\n\n"
               "Keep this key private. It can be activated on up to 3 machines.")
    return key


def verify_paddle_signature(raw_body: bytes, header: str) -> bool:
    """Paddle-Signature: ts=...,h1=...  signed = HMAC_SHA256(secret, 'ts:body')"""
    try:
        parts = dict(p.split("=", 1) for p in header.split(";"))
        ts, h1 = parts["ts"], parts["h1"]
    except Exception:
        return False
    if abs(time.time() - int(ts)) > 300:  # 5-min replay window
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}:".encode() + raw_body,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


def revoke_license(transaction_id: str, email: str = ""):
    db = _load_db()
    key = next((k for k, v in db["licenses"].items()
                if v.get("paddle_txn") == transaction_id), None)
    if not key:
        return None
    db["licenses"][key]["revoked"] = True
    db["licenses"][key]["revoked_at"] = datetime.now(timezone.utc).isoformat()
    _save_db(db)
    recipient = email or db["licenses"][key].get("email", "")
    if recipient and recipient != "unknown":
        send_email(recipient, "Your Xtobe license was revoked",
                   "Your Xtobe Final Guardian license was revoked after a refund "
                   "or payment adjustment.")
    return key


def handle_paddle_event(event: dict):
    event_type = event.get("event_type")
    data = event.get("data", {})
    if event_type == "transaction.completed":
        txn = data.get("id", "")
        existing = next((v for v in _load_db()["licenses"].values()
                         if v.get("paddle_txn") == txn), None)
        if existing:
            return existing.get("key")
        email = (data.get("customer") or {}).get("email") or \
            (data.get("details") or {}).get("customer_email") or "unknown"
        return issue_license(email=email, paddle_txn=txn)
    if event_type == "adjustment.created":
        adjustment = data.get("adjustment", data)
        txn = adjustment.get("transaction_id") or data.get("transaction_id", "")
        if adjustment.get("action") not in ("refund", "revoke", None) and \
           adjustment.get("type") not in ("refund", "revoke"):
            return None
        email = (adjustment.get("customer") or {}).get("email", "")
        return revoke_license(txn, email=email)
    return None


def license_check(payload: dict) -> dict:
    key = payload.get("license_key", "")
    machine = payload.get("machine_id", "")
    db = _load_db()
    lic = db["licenses"].get(key)
    if not lic or lic.get("revoked"):
        return {"valid": False, "reason": "unknown or revoked key"}
    if machine and machine not in lic["machines"]:
        if len(lic["machines"]) >= MAX_MACHINES:
            return {"valid": False, "reason": f"max {MAX_MACHINES} machines reached"}
        lic["machines"].append(machine)
        lic["last_seen"] = datetime.now(timezone.utc).isoformat()
        _save_db(db)
    return {"valid": True, "tier": lic["tier"], "machines_used": len(lic["machines"])}


def update_feed(target: str, arch: str, current: str):
    if current == LATEST_VERSION:
        return None, 204
    fname = f"Xtobe Final Guardian_{LATEST_VERSION}_x64_en-US.msi"
    sig_path = os.path.join(UPDATE_DIR, fname + ".sig")
    if not os.path.exists(sig_path):
        return None, 204
    body = {
        "version": LATEST_VERSION,
        "pub_date": datetime.now(timezone.utc).isoformat(),
        "url": f"{UPDATE_BASE}/{fname.replace(' ', '%20')}",
        "signature": open(sig_path).read().strip(),
        "notes": "Latest Xtobe Final Guardian release.",
    }
    return body, 200


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj=None):
        raw = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        p = urlparse(self.path).path.strip("/").split("/")
        if self.path == "/health":
            try:
                licenses = _load_db().get("licenses", {})
                return self._send(200, {"ok": True, "uptime_seconds": round(time.time() - STARTED_AT),
                                        "license_count": len(licenses),
                                        "config": {"paddle_webhook": bool(WEBHOOK_SECRET),
                                                   "smtp": bool(SMTP_HOST and SMTP_USER and SMTP_PASS)}})
            except Exception as exc:
                return self._send(503, {"ok": False, "error": str(exc)})
        if len(p) == 5 and p[0:2] == ["api", "updates"]:
            body, code = update_feed(p[2], p[3], p[4])
            return self._send(code, body)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/webhooks/paddle":
            raw = self._body()
            if not verify_paddle_signature(raw, self.headers.get("Paddle-Signature", "")):
                return self._send(401, {"error": "bad signature"})
            event = json.loads(raw)
            key = handle_paddle_event(event)
            action = "revoke" if event.get("event_type") == "adjustment.created" else "issue"
            return self._send(200, {"ok": True, "action": action,
                                    "license_issued": action == "issue" and bool(key),
                                    "license_revoked": action == "revoke" and bool(key)})
        if self.path == "/api/license-check":
            try:
                return self._send(200, license_check(json.loads(self._body())))
            except Exception:
                return self._send(400, {"valid": False, "reason": "bad request"})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    print(f"xtobe license server on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
