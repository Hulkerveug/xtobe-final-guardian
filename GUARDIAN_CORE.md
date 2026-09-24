# XTOBE Guardian Core

**Offline AI Security Guardian for Windows.** Guardian Core provides local file scanning, SHA-256 hashing, YARA/heuristic analysis, system status, and security-focused explanations. It does not require Ollama, QEMU, ComfyUI, or a cloud connection.

## Optional Lab features

The application auto-detects optional local services:

- **Ollama** — local AI explanations
- **QEMU** — sandbox Lab
- **ComfyUI** — local image Lab

Missing optional features do not prevent Guardian Core from starting. Run `ai-core/capabilities.py` to inspect the current machine.

## Honest scope



## GLOBAL LANGUAGE POLICY

Guardian automatically adopts the host operating system language.

- All UI elements, reports, notifications, and AI-generated security explanations must respect the active language.
- Manual override is optional via settings (defaulting to System Default).
- No internet connectivity is required for language selection or translation matching.
- Automatic RTL (Right-to-Left) switching applies natively for Arabic, Urdu, and other regional scripts.
- Local Ollama explanations receive the active locale through the sidecar system prompt; no cloud translation service is used.

Guardian Core assists with suspicious-file triage and local analysis. It is not a replacement for Windows Defender, a managed endpoint platform, or professional malware analysis.
