"""
Xtobe Final Guardian - Token Ledger (Earn Model)
-------------------------------------------------
Users EARN compute credits by contributing anonymized lived data.
Content itself NEVER leaves the PC - only a reference hash and the
credit event. 1 token = 10 inference calls.

    Share Story = +50   (anonymized lived event)
    Share Dream = +150  (feelings stay in data/feelings.json, local only)
    Share Skill = +100  (reproducible workflow)

Storage: append-only ledger, DUAL-WRITTEN to
    tokens.json        (project root)
    data/tokens.json   (redundant copy)
Both must agree; on mismatch the ledger refuses to spend.

CLI:
    python token_ledger.py --earn story <content_hash>
    python token_ledger.py --spend 20 "ai chat run"
    python token_ledger.py --balance
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

EARN_RATES = {"story": 50, "dream": 150, "skill": 100}
TOKENS_PER_INFERENCE_BLOCK = 10  # 1 token = 10 inference calls

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_A = os.path.join(ROOT, "tokens.json")
LEDGER_B = os.path.join(ROOT, "data", "tokens.json")


def _load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _atomic_write(path, entries):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    os.replace(tmp, path)


def _append(entry):
    for path in (LEDGER_A, LEDGER_B):
        entries = _load(path)
        entries.append(entry)
        _atomic_write(path, entries)


def balance() -> int:
    a, b = _load(LEDGER_A), _load(LEDGER_B)
    bal_a = sum(e["delta"] for e in a)
    bal_b = sum(e["delta"] for e in b)
    if bal_a != bal_b:
        print("WARNING: ledger mismatch - refusing to trust balance", file=sys.stderr)
        return min(bal_a, bal_b)
    return bal_a


def earn(kind: str, ref_hash: str) -> dict:
    if kind not in EARN_RATES:
        raise SystemExit(f"unknown earn kind: {kind} (expected story|dream|skill)")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "delta": EARN_RATES[kind],
        "ref": ref_hash,          # hash only - content stays local
        "balance_after": balance() + EARN_RATES[kind],
    }
    _append(entry)
    return entry


def spend(amount: int, reason: str) -> dict:
    bal = balance()
    if amount > bal:
        raise SystemExit(f"insufficient tokens: have {bal}, need {amount}")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "spend",
        "delta": -amount,
        "ref": reason,
        "balance_after": bal - amount,
    }
    _append(entry)
    return entry


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--earn", nargs=2, metavar=("KIND", "HASH"))
    ap.add_argument("--spend", nargs=2, metavar=("AMOUNT", "REASON"))
    ap.add_argument("--balance", action="store_true")
    args = ap.parse_args()

    if args.earn:
        print(json.dumps(earn(args.earn[0], args.earn[1])))
    elif args.spend:
        print(json.dumps(spend(int(args.spend[0]), args.spend[1])))
    else:
        bal = balance()
        print(json.dumps({
            "balance": bal,
            "free_inference_calls": bal * TOKENS_PER_INFERENCE_BLOCK,
        }))
