// Xtobe Final Guardian - Tauri v2 entry point.
// Prevents an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod license;
mod state;
mod trial;

use state::AppState;
use std::sync::Mutex;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            guardian_child: Mutex::new(None),
            emulator_child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_system_stats,
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
            license::check_license,
            trial::get_entitlement,
            trial::record_action,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Xtobe Final Guardian");
}
