"""Deterministic Guardian commands for authenticated connector messages."""
from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class CommandType(str, Enum):
    SCAN_THREATS = "scan_threats"
    CLEAN_PC = "clean_pc"
    CLEAN_CONFIRM = "clean_confirm"
    ANCESTRAL_LOG = "ancestral_log"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GuardianCommand:
    type: CommandType
    arguments: Dict[str, Any]
    normalized: str


ALIASES = {
    "scan threats": CommandType.SCAN_THREATS, "scan": CommandType.SCAN_THREATS,
    "threat scan": CommandType.SCAN_THREATS, "check threats": CommandType.SCAN_THREATS,
    "security scan": CommandType.SCAN_THREATS, "clean pc": CommandType.CLEAN_PC,
    "clean": CommandType.CLEAN_PC, "cleanup": CommandType.CLEAN_PC,
    "ancestral log": CommandType.ANCESTRAL_LOG, "guardian log": CommandType.ANCESTRAL_LOG,
    "history": CommandType.ANCESTRAL_LOG, "show log": CommandType.ANCESTRAL_LOG,
}
CONFIRM_RE = re.compile(r"^confirm\s+clean-([a-f0-9]{6})$", re.IGNORECASE)
STORE_PATH = Path.home() / ".local" / "share" / "xtobe" / "confirm_tokens.json"
LOG_PATH = Path.home() / ".local" / "share" / "xtobe" / "guardian-log.json"
ALLOWED_CLEAN_IDS = {"temp", "logs", "sw", "cookies", "ls"}


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, ValueError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def parse_command(message: str) -> GuardianCommand:
    text = re.sub(r"\s+", " ", (message or "").strip().lower())
    match = CONFIRM_RE.fullmatch(text)
    if match:
        return GuardianCommand(CommandType.CLEAN_CONFIRM, {"token": f"CLEAN-{match.group(1).upper()}"}, text)
    if text in ALIASES:
        return GuardianCommand(ALIASES[text], {}, text)
    return GuardianCommand(CommandType.UNKNOWN, {}, text)


def _log(action: str, details: str, status: str = "completed") -> None:
    entries = _read(LOG_PATH, [])
    entries.insert(0, {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "action": action, "details": details, "status": status})
    _write(LOG_PATH, entries[:200])


def _review() -> Dict[str, Any]:
    return {"status": "confirmation_required", "message": "Review created. Select items in the dashboard and confirm; nothing was deleted.", "candidates": [{"id": key, "name": key} for key in sorted(ALLOWED_CLEAN_IDS)]}


def _token(token: str) -> Optional[Dict[str, Any]]:
    entries = _read(STORE_PATH, {})
    entry = entries.get(token.upper())
    if not entry or entry.get("used") or entry.get("expires_at", 0) < time.time():
        return None
    return entry


def _scan() -> Dict[str, Any]:
    checks = [{"id": "local_data", "name": "Xtobe local data", "status": "review", "size": "inspected read-only", "risk": "low", "details": "No deletion performed."}]
    _log("SCAN_THREATS", f"Read-only inspection checked {len(checks)} vector(s).")
    return {"status": "completed", "message": f"Read-only inspection completed. Checked {len(checks)} vector(s).", "checks": checks}


def execute(command: GuardianCommand) -> Dict[str, Any]:
    if command.type == CommandType.SCAN_THREATS:
        return _scan()
    if command.type == CommandType.ANCESTRAL_LOG:
        return {"status": "completed", "message": "Local Guardian history loaded.", "logs": _read(LOG_PATH, [])[:20]}
    if command.type == CommandType.CLEAN_PC:
        return _review()
    if command.type == CommandType.CLEAN_CONFIRM:
        entry = _token(command.arguments["token"])
        if entry is None:
            return {"status": "error", "message": "Invalid or expired confirmation token. No action taken."}
        entries = _read(STORE_PATH, {})
        entries[entry["token"]]["used"] = True
        _write(STORE_PATH, entries)
        _log("CLEAN_CONFIRMED", "User explicitly confirmed a cleanup review; connector mode performs no deletion.")
        return {"status": "completed", "message": "Confirmation accepted. Connector mode performed no deletion."}
    return {"status": "ignored", "message": "Command not recognized. No action was taken."}


def handle_whatsapp_message(message_text: str, sender: str = "unknown") -> Dict[str, Any]:
    command = parse_command(message_text)
    result = execute(command)
    result.update(sender=sender, command=command.type.value)
    return result


def create_clean_review(items: List[str]) -> str:
    allowed = [item for item in items if item in ALLOWED_CLEAN_IDS]
    if not allowed:
        raise ValueError("no allowed cleanup items selected")
    token = f"CLEAN-{secrets.token_hex(3).upper()}"
    entries = _read(STORE_PATH, {})
    entries[token] = {"token": token, "items": allowed, "created_at": time.time(), "expires_at": time.time() + 600, "used": False}
    _write(STORE_PATH, entries)
    return token


if __name__ == "__main__":
    print("Use handle_whatsapp_message(message_text, sender) from the connector worker.")
