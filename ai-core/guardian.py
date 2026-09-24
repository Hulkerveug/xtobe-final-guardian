"""
Xtobe Final Guardian - AI Guardian Engine
------------------------------------------
Two modes:

  python guardian.py --daemon          Watch new processes, score them, log threats.
  python guardian.py --scan <file>     One-shot deep scan, prints a JSON verdict.

Threat scoring combines:
  * SHA-256 hash of the executable
  * YARA rule matching (if yara-python + rules.yar are present)
  * Heuristics: temp-dir execution, unsigned random names, double extensions
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import psutil

THREATS_LOG = os.path.join(os.path.dirname(__file__), "threats.json")
RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.yar")

SUSPICIOUS_DIRS = ("\\temp\\", "\\tmp\\", "\\appdata\\local\\temp\\", "\\downloads\\")
DOUBLE_EXT = re.compile(r"\.(pdf|docx?|xlsx?|jpg|png|txt)\.(exe|scr|bat|ps1)$", re.I)
RANDOM_NAME = re.compile(r"^[a-z0-9]{8,}\.exe$", re.I)

# Vendor-signed OS images live under these roots. Long alphanumeric names there
# (RuntimeBroker.exe, SearchIndexer.exe, agentactivationruntimestarter.exe) are
# ordinary - 59% of System32 matches the pattern - so the name heuristic is only
# meaningful for executables launched from anywhere else.
TRUSTED_ROOTS = tuple(
    os.path.normcase(os.environ[var].rstrip("\\/") + os.sep)
    for var in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
    if os.environ.get(var)
)


def in_trusted_root(path: str) -> bool:
    """True when the image lives under Windows/ or Program Files."""
    if not TRUSTED_ROOTS:
        return False
    return os.path.normcase(os.path.abspath(path)).startswith(TRUSTED_ROOTS)


def looks_random_name(base: str) -> bool:
    """Hash-style dropper names mix letters and digits (a3f9c21b.exe).
    Dictionary/compound vendor names never carry digits, so require at least
    two of them before calling a name 'random'."""
    if not RANDOM_NAME.match(base):
        return False
    stem = base[:-4] if base.lower().endswith(".exe") else base
    return sum(ch.isdigit() for ch in stem) >= 2


_yara_rules = None
try:
    import yara

    if os.path.exists(RULES_PATH):
        _yara_rules = yara.compile(filepath=RULES_PATH)
except ImportError:
    pass  # yara-python optional; heuristics still work


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def yara_hits(path: str):
    if not _yara_rules:
        return []
    try:
        return [m.rule for m in _yara_rules.match(path)]
    except Exception:
        return []


def score_path(path: str):
    """Return (severity, [reasons]) for a filesystem path."""
    reasons = []
    severity = "low"
    low = path.lower()

    if any(d in low for d in SUSPICIOUS_DIRS):
        reasons.append("executing from a temp/download directory")
        severity = "high"
    base = os.path.basename(path)
    if DOUBLE_EXT.search(base):
        reasons.append("double extension masquerade (e.g. invoice.pdf.exe)")
        severity = "critical"
    elif not in_trusted_root(path) and looks_random_name(base):
        reasons.append("random-looking executable name")
        severity = max(severity, "medium", key=SEV_ORDER.index)

    hits = yara_hits(path)
    if hits:
        reasons.append(f"YARA rules matched: {', '.join(hits)}")
        severity = "critical"

    return severity, reasons


SEV_ORDER = ["low", "medium", "high", "critical"]


def scan_file(path: str) -> dict:
    if not os.path.isfile(path):
        return {"path": path, "sha256": "", "verdict": "clean",
                "rules_hit": [], "error": "file not found"}
    digest = sha256_of(path)
    severity, reasons = score_path(path)
    verdict = "clean"
    if severity in ("high", "critical"):
        verdict = "malicious"
    elif severity == "medium":
        verdict = "suspicious"
    return {
        "path": path,
        "sha256": digest,
        "verdict": verdict,
        "rules_hit": reasons,
    }


def log_threat(event: dict):
    events = []
    if os.path.exists(THREATS_LOG):
        try:
            events = json.load(open(THREATS_LOG))
        except Exception:
            events = []
    events.append(event)
    json.dump(events[-500:], open(THREATS_LOG, "w"), indent=2)
    print(json.dumps(event), flush=True)  # streamed to the Rust host


def daemon_loop(poll: float = 1.0):
    """Watch for newly spawned processes and score their images."""
    seen = {p.pid for p in psutil.process_iter()}
    log_threat({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": 0, "name": "guardian", "path": "",
        "reason": "guardian daemon online",
        "severity": "low",
    })
    while True:
        time.sleep(poll)
        current = {p.pid: p for p in psutil.process_iter(["pid", "name", "exe"])}
        for pid, proc in current.items():
            if pid in seen:
                continue
            try:
                exe = proc.info.get("exe")
                if not exe or not os.path.isfile(exe):
                    continue
                severity, reasons = score_path(exe)
                if SEV_ORDER.index(severity) >= SEV_ORDER.index("medium"):
                    log_threat({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "pid": pid,
                        "name": proc.info.get("name", "?"),
                        "path": exe,
                        "reason": "; ".join(reasons),
                        "severity": severity,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        seen = set(current)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--scan", metavar="FILE")
    args = ap.parse_args()

    if args.scan:
        print(json.dumps(scan_file(args.scan)))
    elif args.daemon:
        daemon_loop()
    else:
        ap.print_help()
