"""Detect Guardian Core and optional local Lab capabilities without dependencies."""
import json
import shutil
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def check_ollama() -> bool:
    return bool(shutil.which("ollama")) or _port_open(11434)


def check_qemu() -> bool:
    return bool(shutil.which("qemu-system-x86_64") or shutil.which("qemu-system-x86_64.exe"))


def check_comfyui() -> bool:
    return _port_open(8188)


def get_capabilities() -> dict:
    return {
        "core": True,
        "ollama": check_ollama(),
        "qemu": check_qemu(),
        "comfyui": check_comfyui(),
        "token_ledger": (ROOT / "ai-core" / "token_ledger.py").exists(),
        "license_server": (ROOT / "server" / "license_server.py").exists(),
        "version": "2.0-core",
    }


if __name__ == "__main__":
    print(json.dumps(get_capabilities(), indent=2))
