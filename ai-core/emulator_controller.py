"""
Xtobe Final Guardian - Emulator Controller
-------------------------------------------
Boots a disposable QEMU sandbox (Android-x86 ISO or any disk image).
Untrusted installers run here FIRST; only clean artifacts are promoted
to the host by the Guardian engine.

Requires QEMU on PATH:  https://www.qemu.org/download/#windows
(Install to C:\\Program Files\\qemu and add it to PATH.)

Usage:
    python emulator_controller.py --image emulator/images/android-x86.iso
    python emulator_controller.py --image disk.qcow2 --mem 4096 --cpus 4
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

SNAPSHOT_DIR = os.path.join(tempfile.gettempdir(), "xtobe_sandbox")


def find_qemu() -> str:
    exe = shutil.which("qemu-system-x86_64")
    if not exe:
        default = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
        if os.path.exists(default):
            exe = default
    if not exe:
        print("ERROR: qemu-system-x86_64 not found. Install QEMU and add it to PATH.")
        sys.exit(1)
    return exe


def build_cmd(image: str, mem: int, cpus: int) -> list:
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    return [
        find_qemu(),
        "-m", str(mem),                 # RAM in MB
        "-smp", str(cpus),              # vCPU count
        "-accel", "whpx",               # Windows Hypervisor Platform accel
        "-cdrom", image,                # boot media (ISO); use -hda for qcow2
        "-boot", "d",
        "-snapshot",                    # NEVER write back to the image
        "-nic", "user,model=virtio,hostfwd=tcp::5555-:5555",  # adb forward
        "-display", "sdl",              # simple window; swap for VNC/SPICE later
        "-name", "Xtobe Sandbox",
    ]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--mem", type=int, default=2048)
    ap.add_argument("--cpus", type=int, default=2)
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: image not found: {args.image}")
        print("Download Android-x86 from https://www.android-x86.org into emulator/images/")
        sys.exit(1)

    cmd = build_cmd(args.image, args.mem, args.cpus)
    print(f"Launching sandbox: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd)
    proc.wait()  # keep the controller alive while QEMU runs
