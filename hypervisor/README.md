# Xtobe Hypervisor Package (v5 spec) — honest architecture

## Reality check (read first)

| Claim in the pitch | Engineering truth |
|---|---|
| "Raw KVM ioctl from the Windows app" | `/dev/kvm` does not exist on Windows. KVM and Firecracker are **Linux-only**. |
| "Firecracker microVMs on user PCs" | Firecracker requires Linux + KVM. Cannot run on Windows 11 hosts. |
| "Yocto OS = no EV cert, no SmartScreen" | True, but users must **boot your OS instead of Windows** — kills the $29 consumer funnel. |
| Windows-native equivalent | **WHPX (Windows Hypervisor Platform)** — Hyper-V's user-mode API. Works on Win10/11 Pro & Home (Windows Hypervisor Platform feature). |

## The correct split

```
CONSUMER (today, ships):  Tauri + Python core + QEMU controller  →  $29 MSI, EV-signed, auto-updates
CONSUMER (upgrade path):  swap emulator backend QEMU -> WHPX partition (Rust, windows-rs "Win32_System_Hypervisor")
                          same MSI, feature-detected at runtime, QEMU stays the fallback
INVESTOR / CLOUD (this package):  Linux host + Firecracker + Yocto microVM image
                          each story/dream/skill job runs in an isolated 125ms-boot microVM
                          NO network device attached -> local-only confinement enforced by the VMM
```

## Contents

- `meta-xtobe-guardian/` — Yocto layer building `xtobe-guardian-image` (minimal
  ext4 rootfs with `guardian.py`, `token_ledger.py`, systemd autostart)
- `firecracker/xtobe-microvm.json` — Firecracker VM config (2 vCPU / 512 MiB,
  **no network interface** — hardware-enforced local-only)
- `firecracker/boot.sh` — one-shot microVM launcher

## Build (on a Linux box with KVM)

```bash
git clone https://git.yoctoproject.org/poky -b scarthgap
source poky/oe-init-build-env build-xtobe
bitbake-layers add-layer ../meta-xtobe-guardian
bitbake xtobe-guardian-image     # -> tmp/deploy/images/qemux86-64/xtobe-guardian-image.ext4
# kernel: use Firecracker's recommended upstream quickstart kernel (vmlinux)
./firecracker/boot.sh vmlinux tmp/deploy/images/qemux86-64/xtobe-guardian-image.ext4
```
