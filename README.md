# Xtobe Final Guardian 2.0

Real installable Windows 11 build: **Tauri v2 (Rust + React)** shell, **Python AI sidecar**
(Ollama local LLM + YARA + psutil), and a **QEMU Android-x86 emulator sandbox**.

## Architecture

```
xtobe-final-guardian/
├── src-tauri/            # Rust: system hooks, process scanner, sidecar spawner
│   └── src/commands.rs   #   get_system_stats / list_processes / kill_process
│                         #   start_ai_guardian / scan_file / ask_llm
│                         #   launch_emulator / stop_emulator
├── src/                  # React + Tailwind dashboard
│   └── components/       #   AiCorePanel · ThreatMatrix · EmulatorLab · InstallerBuilder
├── ai-core/              # Python AI guardian
│   ├── guardian.py       #   --daemon (live monitor) · --scan <file> (deep scan)
│   ├── llm_bridge.py     #   offline chat via Ollama (llama3.1 / mistral)
│   ├── emulator_controller.py  # QEMU sandbox launcher (-snapshot, WHPX)
│   └── rules.yar         #   starter YARA ruleset
└── emulator/             # sandbox images + docs
```

## Build the real installer (3 commands)

```powershell
# 0. Prereqs: Node 20+, Rust (rustup), Python 3.11+, Ollama, QEMU
#    plus a window icon: npx tauri icon icon.png   (generates src-tauri/icons/)

# 1. JS deps
npm install

# 2. AI sidecar deps + local model
pip install -r ai-core/requirements.txt
ollama pull llama3.1

# 3. Build -> real .msi installer
npm run tauri build
```

Output:
```
src-tauri/target/release/bundle/msi/Xtobe Final Guardian_2.0.0_x64_en-US.msi
src-tauri/target/release/bundle/nsis/Xtobe Final Guardian_2.0.0_x64-setup.exe
```

Dev mode (hot reload): `npm run tauri dev`

## How the pieces talk

| UI action | Tauri command | Backend |
|---|---|---|
| ACTIVATE GUARDIAN | `start_ai_guardian` | spawns `guardian.py --daemon` (no console window) |
| Threat Matrix refresh | `list_processes` | Rust `sysinfo`, risk-classified in `commands.rs` |
| KILL button | `kill_process` | Rust `sysinfo` terminate |
| AI chat | `ask_llm` | `llm_bridge.py` → local Ollama |
| Deep file scan | `scan_file` | `guardian.py --scan` → SHA-256 + YARA + heuristics → JSON |
| BOOT SANDBOX | `launch_emulator` | `emulator_controller.py` → QEMU `-snapshot` |
| License activation | `check_license` | heartbeat → `/api/license-check`, 7-day offline grace |

## Monetization: $29 Lifetime + Earn

| Tier | What user gets |
|---|---|
| **Free Trial** | 7 days full + 100 free actions |
| **Lifetime $29** | Full local agent forever + earning unlocked |
| **Pro $99** | Heavy automation, memory, team guard |

Earning (compute credits, not cash — `ai-core/token_ledger.py`):
Share Story **+50** · Share Dream **+150** · Share Skill **+100**.
1 token = 10 inference calls → 520 tokens ≈ 5,200 free AI runs.
Content never leaves the PC — only a reference hash is ledgered;
feelings stay in `data/feelings.json`. Ledger dual-writes to
`tokens.json` + `data/tokens.json` (append-only, atomic, refuses spend on mismatch).

## Standalone Python Core (runs as a system app)

```powershell
run.bat        # interactive: banner + earn menu + lockdown checks
```

```
========================================
  XTOBE FINAL GUARDIAN v2.0 - ONLINE
  Local Only - Guard 0 Failures
  Lockdown 12/12 PASS - Balance 520
========================================
Earn:  [1] Story +50   [2] Dream +150   [3] Skill +100
```

Autostart on boot: `Win + R` → `shell:startup` → drop a shortcut to `run.bat`.
`guardian-core/app.py --selftest` runs the 12-point lockdown non-interactively.

Single-file exe (no Tauri needed for the core):
```powershell
pip install pyinstaller
pyinstaller --onefile --name XtobeFinalGuardian guardian-core/app.py
```

## Auto-Updater

Tauri updater plugin is wired end-to-end (`src/updater.ts` → header status line).
One-time setup:

```powershell
npm run tauri signer generate -- -w "$env:USERPROFILE\.tauri\xtobe.key"
# paste the printed public key into tauri.conf.json -> plugins.updater.pubkey
```

Release flow: build → sign artifacts with the private key → upload MSI + signature
to `https://xtobe.app/api/updates/{target}/{arch}/{version}`. The app checks
silently on boot, installs in background, applies on restart. Fails soft offline.

## Protect & Sign (shipping checklist)

```powershell
$env:EV_CERT_THUMBPRINT = "A1B2C3..."   # EV cert on hardware token
.\scripts\protect_build.ps1
```

1. **Obfuscate** — PyArmor (`--restrict --enable-jit --mix-str`) scrambles the
   Python sidecar. Rust needs nothing: native binary, `strip + lto` already on.
2. **Sign** — EV code-signing cert via `signtool` (SHA-256 + DigiCert timestamp)
   on the `.exe`, `.msi` and NSIS setup → no SmartScreen warnings.
3. **License** — heartbeat model (`src-tauri/src/license.rs`), no static keys,
   7-day offline grace. Pair with Keygen.sh or your own `/api/license-check`.
4. **Keys** — BYO-Key: user's own API keys in local `.env`; the app never
   phones home with them.
5. **Checkout** — Paddle / LemonSqueezy as Merchant of Record (handles VAT).

## Sell & Serve (Paddle $29 Lifetime)

```
Landing "Buy Lifetime — $29"  ->  web/paddle-checkout.js  (Paddle overlay)
Paddle payment completed      ->  POST /webhooks/paddle   (HMAC-SHA256 verified)
server/license_server.py      ->  issues XTOBE-XXXX-... key, emails buyer
App activation                ->  POST /api/license-check (max 3 machines, heartbeat)
Auto-updates                  ->  GET  /api/updates/{target}/{arch}/{version}
```

- `server/license_server.py` — stdlib-only (zero pip deps), tested end-to-end
  by `server/smoke_test.py` (bad-signature rejection, key issuance, heartbeat,
  machine cap, updater feed).
- Paddle dashboard setup: create $29 one-time price → copy client token +
  price id into `web/paddle-checkout.js` → approve domain `xtobe.app` →
  set webhook URL + `PADDLE_WEBHOOK_SECRET` env on the server.
