# Emulator Lab — Sandbox Images

Place bootable images here:

```
emulator/
└── images/
    ├── android-x86.iso     # https://www.android-x86.org (recommended first sandbox)
    └── sandbox.qcow2       # optional persistent disk for repeat testing
```

## Requirements
1. **QEMU for Windows** — https://www.qemu.org/download/#windows
   - Install to `C:\Program Files\qemu` and add it to `PATH`.
2. **Windows Hypervisor Platform** enabled (for WHPX acceleration):
   ```powershell
   dism /online /enable-feature /featurename:HypervisorPlatform /all
   ```

## Policy
- QEMU always boots with `-snapshot`: **nothing persists** to the image.
- adb is forwarded to `localhost:5555` for Android-x86 debugging.
- The Guardian promotes files to the host only after a clean sandbox run.
