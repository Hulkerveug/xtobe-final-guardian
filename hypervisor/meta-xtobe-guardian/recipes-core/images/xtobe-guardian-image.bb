SUMMARY = "Xtobe Final Guardian — minimal microVM OS image"
DESCRIPTION = "Bootable ext4 rootfs for Firecracker/KVM: python3 + guardian core + \
token ledger. No network stack enabled by default: local-only by design."
LICENSE = "MIT"

inherit core-image

IMAGE_INSTALL = " \
    packagegroup-core-boot \
    ${CORE_IMAGE_EXTRA_INSTALL} \
    python3 \
    python3-json \
    xtobe-guardian \
"

# Minimal: no SSH, no debug tweakes — this is an appliance, not a dev box.
IMAGE_FEATURES = ""
IMAGE_LINGUAS = ""

IMAGE_ROOTFS_SIZE ?= "65536"
IMAGE_ROOTFS_EXTRA_SPACE = "16384"

# Firecracker wants a plain ext4 rootfs.
IMAGE_FSTYPES = "ext4"
