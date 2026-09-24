//! Trial engine - 7 days OR 100 actions, whichever ends first.
//!
//! Flow: trial (full features) -> locked -> paywall -> Paddle -> license key
//! -> license::check_license -> lifetime.
//!
//! State lives in %APPDATA%/XtobeGuardian/trial.json.
//! Anti-rollback: if the system clock moves backwards we keep the highest
//! timestamp ever seen, so turning the clock back never extends the trial.

use crate::license;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

const TRIAL_DAYS: u64 = 7;
const TRIAL_ACTIONS: u32 = 100;

#[derive(Serialize, Deserialize, Default)]
struct TrialState {
    first_run_epoch: u64,
    last_seen_epoch: u64,
    actions_used: u32,
}

#[derive(Serialize, Clone)]
pub struct Entitlement {
    pub mode: String, // "trial" | "lifetime" | "locked"
    pub days_left: i64,
    pub actions_left: i64,
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn state_path() -> PathBuf {
    let base = dirs::config_dir().unwrap_or_else(|| PathBuf::from("."));
    base.join("XtobeGuardian").join("trial.json")
}

fn load_or_init() -> TrialState {
    if let Ok(raw) = fs::read_to_string(state_path()) {
        if let Ok(mut s) = serde_json::from_str::<TrialState>(&raw) {
            // anti-rollback: never trust a clock earlier than what we saw
            let eff = now().max(s.last_seen_epoch);
            s.last_seen_epoch = eff;
            save(&s);
            return s;
        }
    }
    let s = TrialState { first_run_epoch: now(), last_seen_epoch: now(), actions_used: 0 };
    save(&s);
    s
}

fn save(s: &TrialState) {
    if let Some(dir) = state_path().parent() {
        let _ = fs::create_dir_all(dir);
    }
    let _ = fs::write(state_path(), serde_json::to_string_pretty(s).unwrap());
}

fn compute(s: &TrialState) -> Entitlement {
    if license::cached_license_valid() {
        return Entitlement { mode: "lifetime".into(), days_left: -1, actions_left: -1 };
    }
    let elapsed = s.last_seen_epoch.saturating_sub(s.first_run_epoch);
    let days_left = TRIAL_DAYS as i64 - (elapsed / 86_400) as i64;
    let actions_left = TRIAL_ACTIONS as i64 - s.actions_used as i64;
    let mode = if days_left <= 0 || actions_left <= 0 { "locked" } else { "trial" };
    Entitlement { mode: mode.into(), days_left: days_left.max(0), actions_left: actions_left.max(0) }
}

/// Current entitlement without consuming an action. Polled by the UI.
#[tauri::command]
pub fn get_entitlement() -> Entitlement {
    compute(&load_or_init())
}

/// Consume one trial action (AI chat, file scan, sandbox boot...).
/// No-op in lifetime mode; refuses (stays locked) once exhausted.
#[tauri::command]
pub fn record_action() -> Entitlement {
    let mut s = load_or_init();
    let ent = compute(&s);
    if ent.mode == "trial" {
        s.actions_used += 1;
        save(&s);
        return compute(&s);
    }
    ent
}
