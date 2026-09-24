# ============================================================================
# Xtobe Final Guardian - PROTECT + SIGN + BUILD pipeline (Windows 11)
# Stack: Rust (Tauri, native - no .NET decompile risk) + Python AI sidecar.
#
# Usage:
#   $env:EV_CERT_THUMBPRINT = "A1B2C3..."   # from your EV code-signing token
#   .\scripts\protect_build.ps1
# ============================================================================
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

# --- STEP 1: OBFUSCATE the Python AI sidecar with PyArmor -------------------
# Rust needs no obfuscator: it is native code, and Cargo.toml already ships
# with strip + lto (symbols removed, single codegen unit). Only Python
# bytecode is reversible, so we scramble it here.
Write-Host "[1/4] Obfuscating ai-core with PyArmor..." -ForegroundColor Cyan
pip install pyarmor
pyarmor gen --restrict --enable-jit --mix-str `
    --output ai-core-obf `
    ai-core/guardian.py ai-core/llm_bridge.py ai-core/emulator_controller.py ai-core/token_ledger.py

# Point the bundle at the obfuscated sidecar.
Copy-Item ai-core/rules.yar, ai-core/requirements.txt ai-core-obf/ -Force
(Get-Content src-tauri/tauri.conf.json) `
    -replace '\.\./ai-core/\*', '../ai-core-obf/*' |
    Set-Content src-tauri/tauri.conf.json

# --- STEP 2: BUILD the Tauri release ----------------------------------------
Write-Host "[2/4] Building Tauri release..." -ForegroundColor Cyan
npm run tauri build

$BUNDLE = "src-tauri/target/release/bundle"
$EXE    = "src-tauri/target/release/xtobe-final-guardian.exe"
$MSI    = Get-ChildItem "$BUNDLE/msi/*.msi" | Select-Object -First 1
$NSIS   = Get-ChildItem "$BUNDLE/nsis/*-setup.exe" | Select-Object -First 1

# --- STEP 3: EV CODE SIGN (kills SmartScreen) --------------------------------
# EV cert lives on a hardware token - reference it by thumbprint.
# signtool ships with the Windows SDK.
Write-Host "[3/4] Signing binaries with EV certificate..." -ForegroundColor Cyan
if (-not $env:EV_CERT_THUMBPRINT) { throw "Set `$env:EV_CERT_THUMBPRINT first." }

$SIGN = @(
    "sign", "/fd", "sha256",
    "/td", "sha256", "/tr", "http://timestamp.digicert.com",
    "/sha1", $env:EV_CERT_THUMBPRINT
)
foreach ($target in @($EXE, $MSI.FullName, $NSIS.FullName)) {
    if ($target -and (Test-Path $target)) {
        & signtool @SIGN "$target"
        & signtool verify /pa "$target"
        Write-Host "  signed: $target" -ForegroundColor Green
    }
}

# --- STEP 4: CHECKSUMS for your download page --------------------------------
Write-Host "[4/4] Generating SHA-256 checksums..." -ForegroundColor Cyan
Get-FileHash "$($MSI.FullName)", "$($NSIS.FullName)" -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash)  $(Split-Path $_.Path -Leaf)" } |
    Set-Content "$BUNDLE/SHA256SUMS.txt"

Write-Host "`nDONE. Ship the MSI + SHA256SUMS.txt. Connect Paddle to the Buy button." -ForegroundColor Green
