"""Deterministic, offline CRM onboarding workflow.

The module intentionally uses only Python's standard library. It accepts a JSON
request on stdin, validates the skill contract and input, performs atomic local
SQLite upserts, queues rendered messages, and emits a JSON result.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SKILL_ROOT.parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "local_crm.db"
TEMPLATE_DIR = SKILL_ROOT / "templates"
MANIFEST_PATH = SKILL_ROOT / "skill.json"
REQUIRED_COLUMNS = {"phone", "name", "service", "source"}
ALLOWED_TOOLS = {"local_crm.upsert", "template.render", "dispatch.queue"}
ALLOWED_TEMPLATE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_FIELD_CHARS = 10_000


class WorkflowError(ValueError):
    """A deterministic, user-actionable validation failure."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(value: Any) -> str:
    """Return a stable key without guessing a country code.

    An international number must start with `+`. Domestic numbers remain
    digits-only, so this workflow never silently assigns a jurisdiction.
    """
    raw = str(value or "").strip()
    international = raw.startswith("+")
    digits = re.sub(r"[^0-9]", "", raw)
    if not international:
        digits = re.sub(r"^0+", "", digits)
    if len(digits) < 7 or len(digits) > 15 or (international and not raw.startswith("+")):
        raise WorkflowError(f"invalid phone number: {raw!r}")
    return f"+{digits}" if international else digits


def load_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = {"name", "description", "inputs", "tools", "outputs", "idempotency_key"}
    missing = required - manifest.keys()
    if missing or manifest["name"] != "crm_onboarding":
        raise WorkflowError("invalid skill manifest")
    unknown_tools = set(manifest["tools"]) - ALLOWED_TOOLS
    if unknown_tools or manifest["idempotency_key"] != "phone":
        raise WorkflowError("skill manifest contains an unapproved contract")
    return manifest


def load_leads(path: Path) -> list[dict[str, str]]:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_file() or resolved.stat().st_size > MAX_INPUT_BYTES:
        raise WorkflowError("lead file must be a regular file no larger than 5 MiB")
    suffix = resolved.suffix.lower()
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        if suffix == ".csv":
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            if columns != REQUIRED_COLUMNS:
                raise WorkflowError(f"CSV columns must be exactly: {sorted(REQUIRED_COLUMNS)}")
            leads = list(reader)
        elif suffix == ".json":
            value = json.load(handle)
            if not isinstance(value, list):
                raise WorkflowError("JSON lead file must contain an array")
            leads = value
        else:
            raise WorkflowError("lead file extension must be .csv or .json")
    if len(leads) > MAX_ROWS:
        raise WorkflowError(f"lead file exceeds {MAX_ROWS} rows")
    normalized: list[dict[str, str]] = []
    for index, lead in enumerate(leads, start=1):
        if not isinstance(lead, dict):
            raise WorkflowError(f"row {index} must be an object")
        clean = {key: str(lead.get(key, "")).strip() for key in REQUIRED_COLUMNS}
        if any(len(value) > MAX_FIELD_CHARS for value in clean.values()):
            raise WorkflowError(f"row {index} contains an oversized field")
        clean["phone"] = normalize_phone(clean["phone"])
        if not all(clean.values()):
            raise WorkflowError(f"row {index} requires phone, name, service, and source")
        normalized.append(clean)
    return normalized


def render_template(template_id: str, lead: dict[str, str]) -> str:
    if not ALLOWED_TEMPLATE_ID.fullmatch(template_id):
        raise WorkflowError("invalid template id")
    template_path = (TEMPLATE_DIR / f"{template_id}.txt").resolve(strict=True)
    if template_path.parent != TEMPLATE_DIR.resolve():
        raise WorkflowError("template path escaped template directory")
    text = template_path.read_text(encoding="utf-8")
    values = {
        "client_name": lead["name"],
        "service": lead["service"],
        "phone": lead["phone"],
        "source": lead["source"],
    }
    missing = {name for name in PLACEHOLDER.findall(text) if name not in values}
    if missing:
        raise WorkflowError(f"template has unknown placeholders: {sorted(missing)}")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text).strip()


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                phone TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                service TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_queue (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL REFERENCES leads(phone),
                message TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued', 'sent', 'failed')),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_dispatch_status ON dispatch_queue(status, created_at)"
        )


def save_to_local_crm(
    connection: sqlite3.Connection, lead: dict[str, str]
) -> str:
    now = _utc_now()
    connection.execute(
        """
        INSERT INTO leads(phone, name, service, source, created_at, updated_at)
        VALUES(:phone, :name, :service, :source, :now, :now)
        ON CONFLICT(phone) DO UPDATE SET
            name = excluded.name,
            service = excluded.service,
            source = excluded.source,
            updated_at = excluded.updated_at
        """,
        {**lead, "now": now},
    )
    return "upserted"


def queue_dispatch(
    connection: sqlite3.Connection, phone: str, message: str
) -> None:
    connection.execute(
        "INSERT INTO dispatch_queue(id, phone, message, status, created_at) "
        "VALUES(?, ?, ?, 'queued', ?)",
        (str(uuid.uuid4()), phone, message, _utc_now()),
    )


def process_caller_batch(
    lead_file_path: str,
    template_id: str = "welcome_v1",
    db_path: Path = DEFAULT_DB,
) -> list[dict[str, Any]]:
    load_manifest()
    leads = load_leads(Path(lead_file_path))
    initialize_database(db_path)
    results: list[dict[str, Any]] = []
    with closing(sqlite3.connect(db_path)) as connection, connection:
        for lead in leads:
            try:
                crm_status = save_to_local_crm(connection, lead)
                message = render_template(template_id, lead)
                queue_dispatch(connection, lead["phone"], message)
                results.append(
                    {
                        "phone": lead["phone"],
                        "crm_status": crm_status,
                        "dispatch_ready": True,
                        "message": message,
                    }
                )
            except Exception:
                connection.rollback()
                raise
        connection.commit()
    return results


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def run(request: dict[str, Any], db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    if set(request) != {"lead_file_path", "template_id"}:
        raise WorkflowError("request must contain lead_file_path and template_id only")
    template_id = request["template_id"]
    if not isinstance(template_id, str) or not isinstance(request["lead_file_path"], str):
        raise WorkflowError("request values must be strings")
    started = _utc_now()
    results = process_caller_batch(request["lead_file_path"], template_id, db_path)
    payload = {
        "skill": "crm_onboarding",
        "status": "completed",
        "started_at": started,
        "completed_at": _utc_now(),
        "result_count": len(results),
        "results": results,
    }
    audit = PROJECT_ROOT / "logs" / "crm_onboarding_audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({
            "skill": payload["skill"],
            "status": payload["status"],
            "started_at": started,
            "completed_at": payload["completed_at"],
            "result_count": len(results),
        }, separators=(",", ":")) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise WorkflowError("request JSON must be an object")
        print(json.dumps(run(request), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, WorkflowError, sqlite3.Error) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
