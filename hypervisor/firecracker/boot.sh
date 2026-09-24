#!/usr/bin/env bash
# Boot one Xtobe guardian microVM (Linux/KVM host only — Firecracker cannot run on Windows).
# Usage: ./boot.sh <kernel-vmlinux> <rootfs.ext4>
set -euo pipefail
KERNEL="${1:?kernel vmlinux path required}"
ROOTFS="${2:?rootfs ext4 required}"
SOCK="/tmp/xtobe-fc-$$.sock"

firecracker --api-sock "$SOCK" &
FC_PID=$!
sleep 0.2

api() { curl --unix-socket "$SOCK" -s -X PUT "http://localhost/$1" \
        -H 'Content-Type: application/json' -d @"$2"; }

# Minimal config: kernel, rootfs, 2 vCPU / 512 MiB, NO network interface.
jq --arg k "$KERNEL" '.["boot-source"].kernel_image_path=$k' xtobe-microvm.json > .cfg.json
jq --arg r "$ROOTFS" '.drives[0].path_on_host=$r' .cfg.json > .cfg2.json && mv .cfg2.json .cfg.json

jq '."boot-source"'   .cfg.json > .part.json && api boot-source   .part.json
jq '.drives[0]'       .cfg.json > .part.json && api drives/rootfs .part.json
jq '."machine-config"' .cfg.json > .part.json && api machine-config .part.json

curl --unix-socket "$SOCK" -s -X PUT http://localhost/actions \
  -H 'Content-Type: application/json' \
  -d '{"action_type": "InstanceStart"}'

echo "microVM booting (~125ms). Guardian core + token ledger live INSIDE, no NIC attached."
wait $FC_PID
