"""Offline tests for webhook authentication and durable queue behavior."""
import hashlib
import hmac
import importlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

from connector import bridge_server, queue

SECRET = "test-app-secret"
TOKEN = "test-verify-token"
SENDER = "971500000000"
OTHER = "971599999999"


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update({
            "WHATSAPP_APP_SECRET": SECRET,
            "WHATSAPP_VERIFY_TOKEN": TOKEN,
            "WHATSAPP_ALLOWED_SENDERS": SENDER,
        })
        importlib.reload(bridge_server)
        cls.server = bridge_server.ThreadingHTTPServer(("127.0.0.1", 0), bridge_server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/webhook/whatsapp"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "queue.db"
        self.original_db = bridge_server.DB_PATH
        bridge_server.DB_PATH = self.db

    def tearDown(self):
        bridge_server.DB_PATH = self.original_db
        self.temp.cleanup()

    @staticmethod
    def payload(sender=SENDER, body="echo", message_id="wamid.TEST"):
        return {"entry": [{"changes": [{"value": {"messages": [{
            "id": message_id, "from": sender, "type": "text", "text": {"body": body}
        }]}}]}]}

    def post(self, payload, signature=True):
        raw = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if signature:
            digest = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
            headers["X-Hub-Signature-256"] = "sha256=" + digest
        request = urllib.request.Request(self.url, raw, headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_verification_challenge(self):
        url = self.url + f"?hub.mode=subscribe&hub.verify_token={TOKEN}&hub.challenge=challenge-123"
        with urllib.request.urlopen(url, timeout=3) as response:
            self.assertEqual(b"challenge-123", response.read())

    def test_invalid_signature_rejected(self):
        status, body = self.post(self.payload(), signature=False)
        self.assertEqual(401, status)
        self.assertFalse(os.path.exists(self.db))

    def test_exact_sender_allowlist(self):
        status, _ = self.post(self.payload(sender=OTHER))
        self.assertEqual(403, status)
        self.assertEqual(0, queue.claim_one(self.db) is not None)

    def test_authenticated_message_is_durable_and_idempotent(self):
        status, body = self.post(self.payload())
        self.assertEqual((200, {"status": "queued"}), (status, body))
        status, body = self.post(self.payload())
        self.assertEqual((200, {"status": "duplicate"}), (status, body))
        claimed = queue.claim_one(self.db)
        self.assertEqual(SENDER, claimed["sender"])
        self.assertIsNone(queue.claim_one(self.db))

    def test_only_text_is_accepted(self):
        payload = self.payload()
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "sticker"
        status, body = self.post(payload)
        self.assertEqual((200, {"status": "ignored"}), (status, body))

    def test_audio_is_authenticated_and_queued_as_media(self):
        payload = self.payload(body="")
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        message = {"id": "wamid.AUDIO", "from": SENDER, "type": "audio",
                   "audio": {"id": "media-123", "mime_type": "audio/ogg"}}
        payload["entry"][0]["changes"][0]["value"]["messages"] = [message]
        status, body = self.post(payload)
        self.assertEqual((200, {"status": "queued"}), (status, body))
        claimed = queue.claim_one(self.db)
        self.assertEqual("media-123", claimed["media_id"])
        self.assertEqual("audio/ogg", claimed["media_mime"])

    def test_disallowed_mime_is_ignored(self):
        payload = self.payload(body="")
        payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
            "id": "wamid.BAD", "from": SENDER, "type": "document",
            "document": {"id": "media-bad", "mime_type": "application/x-msdownload"}}
        status, body = self.post(payload)
        self.assertEqual((200, {"status": "ignored"}), (status, body))

    def test_failed_task_is_requeued_until_attempt_limit(self):
        message = {"message_id": "id", "sender": SENDER, "body": "echo", "received_at": queue.utc_now()}
        queue.enqueue(message, self.db)
        for _ in range(queue.MAX_ATTEMPTS):
            queue.claim_one(self.db)
            queue.fail("id", "test_failure", self.db)
        with closing(sqlite3.connect(self.db)) as connection:
            status = connection.execute("SELECT status FROM incoming_messages WHERE message_id='id'").fetchone()[0]
        self.assertEqual("failed", status)


if __name__ == "__main__":
    unittest.main()
