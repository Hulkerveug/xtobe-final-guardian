# XTOBE Guardian Core

**Offline AI Security Guardian for Windows.** Guardian Core provides local file scanning, SHA-256 hashing, YARA/heuristic analysis, system status, and security-focused explanations. It does not require Ollama, QEMU, ComfyUI, or a cloud connection.

## Optional Lab features

The application auto-detects optional local services:

- **Ollama** — local AI explanations
- **QEMU** — sandbox Lab
- **ComfyUI** — local image Lab

Missing optional features do not prevent Guardian Core from starting. Run `ai-core/capabilities.py` to inspect the current machine.

## Honest scope

Guardian Core assists with suspicious-file triage and local analysis. It is not a replacement for Windows Defender, a managed endpoint platform, or professional malware analysis.
