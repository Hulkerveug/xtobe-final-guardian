// Xtobe Final Guardian - Tauri v2 entry point.
// Prevents an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod license;
mod state;
mod trial;

use state::AppState;
use std::sync::Mutex;

/// Shipped in `tauri.conf.json` until the real updater key exists.
/// Run `npx tauri signer generate -w <path>` once xtobe.app is live and paste
/// the generated public key into `plugins.updater.pubkey`.
const PUBKEY_PLACEHOLDER: &str = "REPLACE_WITH_TAURI_SIGNER_PUBKEY";

fn main() {
    let context = tauri::generate_context!();

    // tauri-plugin-updater REQUIRES `plugins.updater.pubkey`: plugin init fails
    // hard when the field is missing (or blank), and because release builds use
    // `panic = "abort"` that failure killed the process before any window
    // appeared. Register the plugin only once a real key is configured so a
    // half-finished updater setup can never brick the app again.
    let configured_pubkey = context
        .config()
        .plugins
        .0
        .get("updater")
        .and_then(|plugin| plugin.get("pubkey"))
        .and_then(|key| key.as_str())
        .map(str::trim)
        .filter(|key| !key.is_empty() && *key != PUBKEY_PLACEHOLDER)
        .map(String::from);

    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            guardian_child: Mutex::new(None),
            emulator_child: Mutex::new(None),
        });

    if configured_pubkey.is_some() {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
    }

    if let Err(err) = builder
        .invoke_handler(tauri::generate_handler![
            commands::get_system_stats,
            commands::get_system_locale,
            commands::preview_local_voice,
            commands::list_processes,
            commands::kill_process,
            commands::start_ai_guardian,
            commands::scan_file,
            commands::ask_llm,
            commands::generate_image,
            commands::launch_emulator,
            commands::stop_emulator,
            commands::get_token_balance,
            commands::earn_tokens,
            commands::get_capabilities,
            license::check_license,

            trial::get_entitlement,
            trial::record_action,
        ])
        .run(context)
    {
        // A windows-subsystem binary prints nothing on failure, so persist the
        // reason next to the trial/license state instead of dying silently.
        let dir = dirs::config_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join("XtobeGuardian");
        let _ = std::fs::create_dir_all(&dir);
        let _ = std::fs::write(dir.join("startup-error.log"), format!("{err}\n"));
        std::process::exit(1);
    }
}
