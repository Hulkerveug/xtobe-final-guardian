"""Authenticated WhatsApp Cloud API webhook for the local Xtobe node."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from connector import queue

MAX_BODY_BYTES = 256 * 1024
MAX_TEXT_CHARS = 4096
DB_PATH = Path(os.environ.get("XTOBE_CONNECTOR_DB", queue.DEFAULT_DB))
ALLOWED_SENDERS = frozenset(
    item.strip() for item in os.environ.get("WHATSAPP_ALLOWED_SENDERS", "").split(",") if item.strip()
)


def signature_valid(raw: bytes, header: Optional[str], secret: str) -> bool:
    if not header or not header.startswith("sha256=") or not secret:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def extract_text_message(payload: dict[str, Any]) -> Optional[dict[str, str]]:
    """Extract one bounded text or supported media event from Meta's payload."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        if value.get("statuses"):
            return None
        message = value["messages"][0]
        sender = str(message["from"])
        message_id = str(message["id"])
        kind = message.get("type", "text")
        if len(message_id) > 256:
            return None
        result = {"message_id": message_id, "sender": sender, "body": "", "received_at": queue.utc_now()}
        if kind == "text":
            body = message["text"]["body"].strip()
            if not body or len(body) > MAX_TEXT_CHARS:
                return None
            result["body"] = body
            return result
        if kind not in ("audio", "document", "image"):
            return None
        item = message[kind]
        mime = str(item.get("mime_type", "")).lower()
        if mime not in queue.ALLOWED_MEDIA_MIME:
            return None
        media_id = str(item.get("id", ""))
        if not media_id or len(media_id) > 512:
            return None
        result.update(media_id=media_id, media_mime=mime,
                      media_filename=str(item.get("filename", ""))[:255])
        return result
    except (KeyError, IndexError, TypeError):
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "XtobeConnector/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Never log headers, body, phone numbers, or command text.
        return

    def reply(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/webhook/whatsapp":
            self.reply(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        query = parse_qs(parsed.query)
        expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
        mode = query.get("hub.mode", [""])[0]
        token = query.get("hub.verify_token", [""])[0]
        challenge = query.get("hub.challenge", [""])[0]
        if expected_token and mode == "subscribe" and hmac.compare_digest(token, expected_token):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(challenge.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
        else:
            self.reply(HTTPStatus.FORBIDDEN, {"error": "forbidden"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/webhook/whatsapp":
            self.reply(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.reply(HTTPStatus.BAD_REQUEST, {"error": "invalid_length"})
            return
        if length < 1 or length > MAX_BODY_BYTES:
            self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_length"})
            return
        raw = self.rfile.read(length)
        secret = os.environ.get("WHATSAPP_APP_SECRET", "")
        if not signature_valid(raw, self.headers.get("X-Hub-Signature-256"), secret):
            self.reply(HTTPStatus.UNAUTHORIZED, {"error": "invalid_signature"})
            return
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            self.reply(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        message = extract_text_message(payload)
        if message is None:
            self.reply(HTTPStatus.OK, {"status": "ignored"})
        elif message["sender"] not in ALLOWED_SENDERS:
            self.reply(HTTPStatus.FORBIDDEN, {"error": "sender_not_allowed"})
        else:
            inserted = queue.enqueue(message, DB_PATH)
            self.reply(HTTPStatus.OK, {"status": "queued" if inserted else "duplicate"})


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    if not os.environ.get("WHATSAPP_APP_SECRET") or not ALLOWED_SENDERS:
        raise RuntimeError("WHATSAPP_APP_SECRET and WHATSAPP_ALLOWED_SENDERS are required")
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    serve(os.environ.get("XTOBE_CONNECTOR_HOST", "127.0.0.1"), int(os.environ.get("XTOBE_CONNECTOR_PORT", "8000")))
