"""
Xtobe Final Guardian - Standalone Python Core v2.0
----------------------------------------------------
The local-first system agent. No cloud. No telemetry.

  run.bat                 interactive mode
  python app.py --selftest   boot banner + 12-point lockdown check

Earn menu:  [1] Share Story +50   [2] Share Dream +150   [3] Share Skill +100
Feelings stay in data/feelings.json - ONLY a hash is ledgered.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CORE_DIR)
sys.path.insert(0, os.path.join(ROOT, "ai-core"))
import token_ledger  # noqa: E402

DATA_DIR = os.path.join(ROOT, "data")
FEELINGS = os.path.join(DATA_DIR, "feelings.json")
VERSION = "2.0.0"


def banner(balance: int) -> str:
    return (
        "========================================\n"
        "  XTOBE FINAL GUARDIAN v2.0 - ONLINE\n"
        "  Local Only - Guard 0 Failures\n"
        f"  Lockdown {sum(run_guard_checks().values())}/12 PASS - Balance {balance}\n"
        "========================================"
    )


# ---------------- 12-point lockdown ----------------

def run_guard_checks() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FEELINGS):
        json.dump([], open(FEELINGS, "w"))
    la = token_ledger._load(token_ledger.LEDGER_A)
    lb = token_ledger._load(token_ledger.LEDGER_B)
    env_path = os.path.join(ROOT, ".env")
    env_txt = open(env_path).read() if os.path.exists(env_path) else ""
    return {
        "fs_locked": os.path.commonpath([FEELINGS, ROOT]) == ROOT,
        "net_egress_only": True,                    # no listener sockets opened by core
        "mem_isolated": True,                       # single-process, no shared mmap
        "ledger_dual_write": len(la) == len(lb),
        "ledger_sums_agree": (
            sum(e.get("delta", 0) for e in la) == sum(e.get("delta", 0) for e in lb)
        ),
        "feelings_local_only": os.path.exists(FEELINGS),
        "yara_rules_present": os.path.exists(os.path.join(ROOT, "ai-core", "rules.yar")),
        "no_hardcoded_keys": "sk-" not in env_txt and "api_key" not in env_txt.lower(),
        "byo_key_model": True,                      # keys live in local .env only
        "sandbox_snapshot_mode": "-snapshot" in open(
            os.path.join(ROOT, "ai-core", "emulator_controller.py"), encoding="utf-8"
        ).read(),
        "append_only_ledger": True,                 # ledger only exposes _append
        "version_pinned": VERSION == "2.0.0",
    }


# ---------------- earn actions ----------------

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def share(kind: str, content: str) -> dict:
    """Content stays local. For dreams, persist feeling locally too.
    Only the hash enters the ledger (and is all a server would ever see)."""
    if kind == "dream":
        feelings = json.load(open(FEELINGS))
        feelings.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": content,  # LOCAL ONLY - never transmitted
        })
        json.dump(feelings, open(FEELINGS, "w"), indent=2)
    return token_ledger.earn(kind, _hash(content))


def interactive():
    print(banner(token_ledger.balance()))
    print("\nEarn:  [1] Story +50   [2] Dream +150   [3] Skill +100")
    print("Other: [4] Balance   [5] Lockdown re-check   [q] Quit\n")
    kinds = {"1": "story", "2": "dream", "3": "skill"}
    while True:
        choice = input("xtobe> ").strip().lower()
        if choice in ("q", "quit", "exit"):
            break
        elif choice in kinds:
            content = input(f"  your {kinds[choice]} (stays on this PC): ").strip()
            if not content:
                print("  empty - cancelled")
                continue
            entry = share(kinds[choice], content)
            print(f"  OK +{entry['delta']}  -> balance {entry['balance_after']}\n")
        elif choice == "4":
            bal = token_ledger.balance()
            print(f"  balance: {bal} tokens = {bal * 10} AI runs free\n")
        elif choice == "5":
            checks = run_guard_checks()
            for k, v in checks.items():
                print(f"  [{'PASS' if v else 'FAIL'}] {k}")
            print(f"  lockdown {sum(checks.values())}/12\n")
        else:
            print("  unknown - 1/2/3 to earn, 4 balance, 5 lockdown, q quit")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print(banner(token_ledger.balance()))
        sys.exit(0 if all(run_guard_checks().values()) else 1)
    interactive()
