# XTOBE Final Guardian 2.0

> **Offline AI Security Guardian for Windows.** Local file scanning, YARA/heuristic analysis, and optional Lab features. Works offline with no cloud required.

Guardian Core is the primary product: choose a file, inspect its hash and indicators, and receive a local security verdict. Ollama, QEMU, and ComfyUI are optional Lab features and are auto-detected; Guardian Core does not require them.

See [GUARDIAN_CORE.md](GUARDIAN_CORE.md) for the product boundary and [SECURITY_TESTING.md](SECURITY_TESTING.md) for measured testing status.

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

## Cross-platform Electron deployment (optional shell)

The primary Windows desktop release is the Tauri application documented above. The repository also contains a separate, context-isolated Electron shell under `electron/` for local cross-platform testing. Do not mix Electron IPC into the Tauri renderer; the Tauri shell remains the source of truth for `start_ai_guardian`, `list_processes`, and `get_token_balance`.

### Requirements

- Node.js 20+
- npm
- Python 3.11+ for the local AI sidecar
- Rust 1.77+ when building the Tauri application
- Platform-specific native tooling only when producing signed installers

Verify Node.js:

```powershell
node -v
npm -v
```

Install JavaScript dependencies:

```powershell
Set-Location C:\Users\Nishan\Xtobe\xtobe-final-guardian
npm install
```

### Web preview

```powershell
npm run dev
```

Open the local Vite URL printed by Vite, normally:

```text
http://127.0.0.1:5173/
```

### Tauri native development and release

```powershell
$env:PATH = "C:\Users\Nishan\.cargo\bin;" + $env:PATH
npm run tauri dev
npx tauri build
```

The Tauri release executable is written under:

```text
src-tauri/target/release/
```

The Windows desktop shortcut targets the standalone executable in that directory.

### Optional Electron shell

The checked-in Electron shell is a separate local-testing application. It uses a preload bridge with `contextIsolation`, `nodeIntegration: false`, and `sandbox: true`:

```powershell
npm run electron
```

To package the Electron shell, install the packager in the release environment and provide platform-specific icons before invoking it:

```powershell
npm install --save-dev electron-builder
npx electron-builder --win
```

The proposed cross-platform targets are:

```text
Windows  -> NSIS installer
macOS    -> DMG
Linux    -> AppImage and DEB
```

The exact Electron Builder configuration must be kept separate from `tauri.conf.json`. The current repository does not include production `build/icon.ico`, `build/icon.icns`, signing certificates, or native notification/tray implementations. Do not claim those release artifacts are available until they are added and tested.

### Security and behavior

The Electron shell must never:

- expose raw `ipcRenderer` to the renderer
- enable Node.js in the page
- accept arbitrary shell commands from messages
- silently delete temporary files
- report process telemetry as a malware verdict
- send local data to a cloud service by default

Process and CPU data are read-only telemetry. They must be labeled as metrics, not threat verdicts. The Electron renderer must show `BRIDGE OFFLINE` when the preload bridge is unavailable rather than using fabricated fallback values.

### Auto-start

Auto-start is opt-in and should be configured per platform only after packaging is tested:

- Windows: installer or user-approved startup entry
- macOS: user-approved Login Items
- Linux: user-approved desktop autostart entry

Do not silently enable auto-start during installation.


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
`scripts/rule_regression.py` re-checks the detection rules against real Windows
binaries plus synthetic droppers (needs `yara-python`), so the false positives
fixed in 2.0.0 cannot creep back.

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
