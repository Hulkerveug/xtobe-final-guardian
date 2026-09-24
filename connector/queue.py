"""Durable SQLite inbox for authenticated WhatsApp messages."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "connector_queue.db"
MAX_ATTEMPTS = 3
MAX_MEDIA_BYTES = 20 * 1024 * 1024
ALLOWED_MEDIA_MIME = {
    "audio/ogg", "audio/mpeg", "audio/mp4", "audio/amr", "audio/aac",
    "application/pdf", "application/json", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg", "image/png", "image/webp",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize(path: Path = DEFAULT_DB) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incoming_messages (
                message_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                body TEXT NOT NULL,
                received_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued','processing','done','failed')),
                attempts INTEGER NOT NULL DEFAULT 0,
                claimed_at TEXT,
                completed_at TEXT,
                error_code TEXT,
                media_id TEXT,
                media_mime TEXT,
                media_filename TEXT
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(incoming_messages)")}
        for name, definition in (("media_id", "TEXT"), ("media_mime", "TEXT"), ("media_filename", "TEXT")):
            if name not in columns:
                connection.execute(f"ALTER TABLE incoming_messages ADD COLUMN {name} {definition}")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_incoming_claim "
            "ON incoming_messages(status, received_at)"
        )


def enqueue(message: dict[str, Any], path: Path = DEFAULT_DB) -> bool:
    """Insert once by Meta message ID. Returns False for a replay."""
    initialize(path)
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO incoming_messages"
            "(message_id,sender,body,received_at,status,media_id,media_mime,media_filename) "
            "VALUES(?,?,?,?, 'queued',?,?,?)",
            (message["message_id"], message["sender"], message.get("body", ""),
             message["received_at"], message.get("media_id"), message.get("media_mime"),
             message.get("media_filename")),
        )
        return bool(cursor.rowcount)


def requeue_expired(path: Path = DEFAULT_DB, lease_seconds: int = 300) -> int:
    """Return abandoned claims to queued; completion is idempotent by message ID."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=lease_seconds)).isoformat()
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        cursor = connection.execute(
            "UPDATE incoming_messages SET status='queued',claimed_at=NULL "
            "WHERE status='processing' AND claimed_at < ? AND attempts < ?",
            (cutoff, MAX_ATTEMPTS),
        )
        return int(cursor.rowcount)


def claim_one(path: Path = DEFAULT_DB) -> Optional[dict[str, str]]:
    initialize(path)
    with closing(sqlite3.connect(path, timeout=10, isolation_level=None)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT message_id,sender,body,attempts,media_id,media_mime,media_filename FROM incoming_messages "
            "WHERE status='queued' ORDER BY received_at LIMIT 1"
        ).fetchone()
        if row is None:
            connection.rollback()
            return None
        now = utc_now()
        connection.execute(
            "UPDATE incoming_messages SET status='processing',attempts=attempts+1,claimed_at=? "
            "WHERE message_id=? AND status='queued'", (now, row[0])
        )
        connection.commit()
        return dict(zip(("message_id", "sender", "body", "attempts", "media_id", "media_mime", "media_filename"), row))


def complete(message_id: str, path: Path = DEFAULT_DB) -> None:
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        connection.execute(
            "UPDATE incoming_messages SET status='done',completed_at=?,error_code=NULL "
            "WHERE message_id=?", (utc_now(), message_id)
        )


def fail(message_id: str, code: str, path: Path = DEFAULT_DB) -> None:
    code = code[:32]
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        connection.execute(
            "UPDATE incoming_messages SET status=CASE WHEN attempts >= ? THEN 'failed' "
            "ELSE 'queued' END,error_code=? WHERE message_id=?",
            (MAX_ATTEMPTS, code, message_id),
        )
