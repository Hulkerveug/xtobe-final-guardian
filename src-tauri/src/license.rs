//! License heartbeat - Keygen.sh / Paddle compatible.
//!
//! No static keys shipped in the binary. On activation the app POSTs the
//! user-entered key to the license server; on success it caches a local
//! receipt granting a 7-day OFFLINE GRACE so the app never locks out a
//! paying user who is simply offline.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const LICENSE_ENDPOINT: &str = "https://api.xtobe.dev/api/license-check";
const OFFLINE_GRACE_SECS: u64 = 7 * 24 * 60 * 60; // 7 days

#[derive(Serialize, Deserialize)]
struct LicenseCache {
    key: String,
    machine: String,
    last_ok_epoch: u64,
}

#[derive(Serialize)]
pub struct LicenseStatus {
    pub valid: bool,
    pub source: String, // "server" | "offline-grace" | "none"
    pub offline_days_left: i64,
}

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or(Duration::ZERO)
        .as_secs()
}

/// Stable machine fingerprint: hash of COMPUTERNAME + USERNAME.
/// Never leaves the device except inside the license POST.
fn machine_id() -> String {
    let raw = format!(
        "{}::{}",
        std::env::var("COMPUTERNAME").unwrap_or_default(),
        std::env::var("USERNAME").unwrap_or_default()
    );
    hex_encode(&Sha256::digest(raw.as_bytes()))
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn cache_path() -> PathBuf {
    let base = dirs::config_dir().unwrap_or_else(|| PathBuf::from("."));
    base.join("XtobeGuardian").join("license.json")
}

fn read_cache() -> Option<LicenseCache> {
    let raw = fs::read_to_string(cache_path()).ok()?;
    serde_json::from_str(&raw).ok()
}

/// True when a license receipt exists for THIS machine and is still inside
/// the offline grace window. Used by the trial engine for lifetime unlock.
pub(crate) fn cached_license_valid() -> bool {
    match read_cache() {
        Some(c) => {
            let age = now_epoch().saturating_sub(c.last_ok_epoch);
            c.machine == machine_id() && age < OFFLINE_GRACE_SECS
        }
        None => false,
    }
}

fn write_cache(key: &str) {
    let cache = LicenseCache {
        key: key.into(),
        machine: machine_id(),
        last_ok_epoch: now_epoch(),
    };
    if let Some(dir) = cache_path().parent() {
        let _ = fs::create_dir_all(dir);
    }
    let _ = fs::write(cache_path(), serde_json::to_string_pretty(&cache).unwrap());
}

/// Heartbeat: server first, 7-day offline grace as fallback.
#[tauri::command]
pub fn check_license(key: String) -> LicenseStatus {
    // Secure input guard (v4.2): only plausible key material ever reaches
    // the network or disk - blocks "..", ".env", slashes, control chars.
    if key.len() > 64
        || key.is_empty()
        || !key.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
    {
        return LicenseStatus { valid: false, source: "none".into(), offline_days_left: 0 };
    }
    // 1) Online heartbeat
    let payload = serde_json::json!({
        "license_key": key,
        "machine_id": machine_id(),
        "product": "xtobe-final-guardian",
        "version": env!("CARGO_PKG_VERSION"),
    });
    let online = ureq::post(LICENSE_ENDPOINT)
        .timeout(Duration::from_secs(5))
        .send_json(payload);

    if let Ok(resp) = online {
        if resp.status() == 200 {
            if let Ok(body) = resp.into_json::<serde_json::Value>() {
                if body.get("valid").and_then(|v| v.as_bool()).unwrap_or(false) {
                    write_cache(&key);
                    return LicenseStatus {
                        valid: true,
                        source: "server".into(),
                        offline_days_left: 7,
                    };
                }
            }
        }
        // Server reachable but key rejected -> hard fail, no grace.
        return LicenseStatus { valid: false, source: "server".into(), offline_days_left: 0 };
    }

    // 2) Offline grace: same key + same machine + within 7 days of last OK.
    if let Some(cache) = read_cache() {
        let age = now_epoch().saturating_sub(cache.last_ok_epoch);
        if cache.key == key && cache.machine == machine_id() && age < OFFLINE_GRACE_SECS {
            return LicenseStatus {
                valid: true,
                source: "offline-grace".into(),
                offline_days_left: ((OFFLINE_GRACE_SECS - age) / 86_400) as i64,
            };
        }
    }

    LicenseStatus { valid: false, source: "none".into(), offline_days_left: 0 }
}
