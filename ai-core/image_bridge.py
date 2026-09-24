#!/usr/bin/env python3
"""image_bridge.py - Offline image generation via local ComfyUI.

Stdlib-only sidecar. Talks to ComfyUI's HTTP API (127.0.0.1:8188),
queues a txt2img workflow, polls history, saves the PNG locally.

Usage:
  python image_bridge.py --prompt "a neon guardian robot" [--size 512] [--steps 8]

Output (stdout, single JSON line):
  {"ok": true,  "file": "<abs path>", "checkpoint": "<name>", "seconds": 12.3}
  {"ok": false, "error": "<why>", "install": "<how to fix>"}

Nothing ever leaves the PC. If ComfyUI is not running, we fail soft
with setup instructions instead of raising.
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
OUT_DIR = Path(__file__).resolve().parent / "generated"
POLL_SECONDS = 240  # CPU-only generation can be slow

INSTALL_HINT = (
    "ComfyUI not reachable. Install once: "
    "git clone https://github.com/comfyanonymous/ComfyUI %USERPROFILE%\\ComfyUI && "
    "cd %USERPROFILE%\\ComfyUI && py -3 -m pip install -r requirements.txt && "
    "drop an SD1.5/SDXL-Turbo .safetensors into models\\checkpoints && "
    "start with: py -3 main.py --cpu   (then retry)"
)


def emit(obj):
    print(json.dumps(obj))
    sys.exit(0 if obj.get("ok") else 1)


def http_json(path, payload=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def pick_checkpoint():
    try:
        names = http_json("/models/checkpoints", timeout=5)
        if isinstance(names, list) and names:
            for n in names:  # prefer turbo/lightning for speed
                if "turbo" in n.lower() or "lightning" in n.lower():
                    return n
            return names[0]
    except Exception:
        pass
    return "v1-5-pruned-emaonly.safetensors"  # common default


def build_workflow(prompt, ckpt, size, steps, seed):
    cfg = 2.0 if "turbo" in ckpt.lower() or "lightning" in ckpt.lower() else 7.0
    return {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": size, "height": size, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "text": "blurry, low quality, watermark, text", "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {
            "samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "xtobe", "images": ["8", 0]}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--steps", type=int, default=8)
    args = ap.parse_args()

    t0 = time.time()
    try:
        http_json("/system_stats", timeout=3)
    except Exception:
        emit({"ok": False, "error": "comfyui_offline", "install": INSTALL_HINT})

    ckpt = pick_checkpoint()
    client = str(uuid.uuid4())
    try:
        resp = http_json("/prompt", {
            "prompt": build_workflow(args.prompt, ckpt, args.size, args.steps,
                                     seed=int(time.time()) % 2**31),
            "client_id": client}, timeout=15)
    except urllib.error.HTTPError as e:
        emit({"ok": False, "error": f"workflow rejected: {e.read().decode()[:300]}",
              "checkpoint": ckpt})
    pid = resp.get("prompt_id")
    if not pid:
        emit({"ok": False, "error": f"no prompt_id returned: {resp}"})

    deadline = t0 + POLL_SECONDS
    while time.time() < deadline:
        time.sleep(2)
        try:
            hist = http_json(f"/history/{pid}", timeout=5)
        except Exception:
            continue
        entry = hist.get(pid)
        if not entry:
            continue
        outs = entry.get("outputs", {})
        for node in outs.values():
            for img in node.get("images", []):
                q = (f"/view?filename={img['filename']}"
                     f"&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}")
                try:
                    with urllib.request.urlopen(COMFY + q, timeout=30) as r:
                        data = r.read()
                except Exception as e:
                    emit({"ok": False, "error": f"download failed: {e}"})
                OUT_DIR.mkdir(exist_ok=True)
                dest = OUT_DIR / f"xtobe_{int(t0)}.png"
                dest.write_bytes(data)
                emit({"ok": True, "file": str(dest), "checkpoint": ckpt,
                      "prompt": args.prompt,
                      "seconds": round(time.time() - t0, 1)})
        if entry.get("status", {}).get("completed"):
            emit({"ok": False, "error": "finished but no image output found"})
    emit({"ok": False, "error": f"timeout after {POLL_SECONDS}s — still queued in ComfyUI"})


if __name__ == "__main__":
    main()
