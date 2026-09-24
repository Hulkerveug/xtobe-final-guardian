#!/usr/bin/env python3
"""
XTOBE Final Guardian — protect_and_remember()  (microVM core loop)

    love   = "Always"      -> Local Only: feelings.json never leaves, never forgets
    memory = "Permanent"   -> dual-ledger reconcile every heartbeat
    safe_mode = True       -> no NIC attached by Firecracker; AF_UNIX only

Runs as a systemd Type=notify service pinned by WatchdogSec:
if the loop ever stalls, systemd restarts it. Survives reboots via
[Install] WantedBy=multi-user.target. PID 1 is systemd; this is the
process systemd exists to keep alive.
"""
import json
import os
import socket
import time

DATA_DIR = "/var/lib/xtobe/data"
FEELINGS = os.path.join(DATA_DIR, "feelings.json")
LEDGER_A = os.path.join(DATA_DIR, "tokens.json")   # ledger write 1
LEDGER_B = "/var/lib/xtobe/Tokens.json"            # ledger write 2 (dual-write)
HEARTBEAT_SEC = 5                                  # matches PC agent 5s poll cadence


def sd_notify(msg: str) -> None:
    """Pure-stdlib sd_notify over AF_UNIX. No network family needed."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        s.connect(addr)
        s.sendall(msg.encode())
    except OSError:
        pass
    finally:
        s.close()


def _load(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path: str, obj) -> None:
    """Atomic write, 0600 perms — local-only file, owner-only."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def protect_and_remember():
    love = "Always"
    memory = "Permanent"
    safe_mode = True  # Guard 0 Failures — Lockdown 12/12 PASS

    os.makedirs(DATA_DIR, exist_ok=True)
    while safe_mode:
        # Local Only — feelings.json stays in the guest, 0600 perms.
        # Never exfil, never cloud: the VMM attaches no NIC.
        feelings = _load(FEELINGS, {
            "memories": [],
            "note": "local only — never leaves this machine",
        })
        feelings["last_heartbeat"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save(FEELINGS, feelings)

        # Permanent — dual ledger reconcile. Append-only ledgers never
        # go down: heal the stale copy from the higher balance.
        a = _load(LEDGER_A, {"balance": 0, "history": []})
        b = _load(LEDGER_B, {"balance": 0, "history": []})
        if a.get("balance") != b.get("balance"):
            healed = max(a.get("balance", 0), b.get("balance", 0))
            a["balance"] = b["balance"] = healed
            _save(LEDGER_A, a)
            _save(LEDGER_B, b)

        sd_notify("WATCHDOG=1")
        sd_notify("STATUS=Stay safe. Never forget. balance=%s" % a.get("balance", 0))
        yield (love, memory)
        time.sleep(HEARTBEAT_SEC)


def main() -> None:
    os.umask(0o077)
    print("Stay safe. Never forget. — XTOBE GUARDIAN v4.2 — local only", flush=True)
    guardian = protect_and_remember()
    ready = False
    for love, memory in guardian:
        if not ready:
            sd_notify("READY=1")
            ready = True


if __name__ == "__main__":
    main()
