use crate::state::AppState;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::SystemTime;
use sysinfo::{Pid, System};
use tauri::State;

#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

// ---------- DTOs ----------

#[derive(Serialize)]
pub struct SystemStats {
    cpu_usage: f32,
    mem_used_gb: f64,
    mem_total_gb: f64,
    process_count: usize,
    guardian_active: bool,
}

#[derive(Serialize)]
pub struct ProcessInfo {
    pid: u32,
    name: String,
    exe: Option<String>,
    cpu: f32,
    mem_mb: f64,
    risk: String, // "safe" | "warn" | "danger"
}

#[derive(Serialize)]
pub struct EmulatorStatus {
    running: bool,
    image: Option<String>,
    pid: Option<u32>,
}

// ---------- helpers ----------

fn ai_core_dir() -> PathBuf {
    // Dev: <repo>/ai-core. Release: resources are bundled next to the exe.
    if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
        let dev = PathBuf::from(manifest).join("..").join("ai-core");
        if dev.exists() {
            return dev;
        }
    }
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.join("ai-core")))
        .unwrap_or_else(|| PathBuf::from("ai-core"))
}

fn python_cmd(script: &str) -> Command {
    // Resolve a real Python interpreter once. Bare `python` on Windows often
    // resolves to the Microsoft Store alias stub (exits non-zero), so probe
    // candidates with `--version` and cache the first one that works.
    static PYTHON: std::sync::OnceLock<(String, Vec<String>)> = std::sync::OnceLock::new();
    let (exe, pre) = PYTHON.get_or_init(|| {
        let candidates: [(&str, &[&str]); 3] = [
            ("py", &["-3"][..]), // Windows py launcher (most reliable)
            ("python", &[][..]),
            ("python3", &[][..]),
        ];
        for (exe, pre) in candidates {
            let mut probe = Command::new(exe);
            probe
                .args(pre)
                .arg("--version")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .stdin(Stdio::null());
            #[cfg(windows)]
            probe.creation_flags(CREATE_NO_WINDOW);
            let ok = probe.status().map(|s| s.success()).unwrap_or(false);
            if ok {
                return (exe.to_string(), pre.iter().map(|s| s.to_string()).collect());
            }
        }
        ("python".to_string(), Vec::new()) // last resort; error surfaces at spawn
    });
    let mut c = Command::new(exe);
    c.args(pre).arg(ai_core_dir().join(script));
    #[cfg(windows)]
    c.creation_flags(CREATE_NO_WINDOW);
    c
}

fn run_capture(script: &str, args: &[&str]) -> Result<String, String> {
    let out = python_cmd(script)
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("failed to run {script}: {e}"))?;
    if out.status.success() {
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&out.stderr).trim().to_string())
    }
}

fn classify_risk(exe: &Option<String>) -> &'static str {
    match exe {
        None => "warn", // no path -> kernel/system, can't verify
        Some(p) => {
            let l = p.to_lowercase();
            if l.contains("\\temp\\") || l.contains("\\appdata\\local\\temp\\") {
                "danger" // executable running from temp dirs: classic dropper behavior
            } else if l.contains("\\windows\\") || l.contains("\\program files") {
                "safe"
            } else {
                "warn"
            }
        }
    }
}

// ---------- Tauri commands ----------

#[tauri::command]
pub fn get_system_stats(state: State<AppState>) -> SystemStats {
    let mut sys = System::new_all();
    sys.refresh_all();
    let guardian_active = state
        .guardian_child
        .lock()
        .map(|mut g| g.as_mut().and_then(|c| c.try_wait().ok().flatten()).is_none() && g.is_some())
        .unwrap_or(false);
    SystemStats {
        cpu_usage: sys.global_cpu_info().cpu_usage(),
        mem_used_gb: sys.used_memory() as f64 / 1_073_741_824.0,
        mem_total_gb: sys.total_memory() as f64 / 1_073_741_824.0,
        process_count: sys.processes().len(),
        guardian_active,
    }
}

#[tauri::command]
pub fn list_processes() -> Vec<ProcessInfo> {
    let mut sys = System::new_all();
    sys.refresh_all();
    sys.processes()
        .iter()
        .map(|(pid, p)| {
            let exe = p.exe().map(|e| e.to_string_lossy().to_string());
            ProcessInfo {
                pid: pid.as_u32(),
                name: p.name().to_string(),
                risk: classify_risk(&exe).to_string(),
                exe,
                cpu: p.cpu_usage(),
                mem_mb: p.memory() as f64 / 1_048_576.0,
            }
        })
        .collect()
}

#[tauri::command]
pub fn kill_process(pid: u32) -> bool {
    let mut sys = System::new_all();
    sys.refresh_all();
    sys.process(Pid::from_u32(pid)).map(|p| p.kill()).unwrap_or(false)
}

#[tauri::command]
pub fn start_ai_guardian(state: State<AppState>) -> Result<String, String> {
    let mut guard = state.guardian_child.lock().map_err(|e| e.to_string())?;
    if guard.is_some() {
        return Ok("guardian already running".into());
    }
    let child = python_cmd("guardian.py")
        .arg("--daemon")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("failed to spawn guardian sidecar: {e}"))?;
    *guard = Some(child);
    Ok("guardian sidecar started".into())
}

#[tauri::command]
pub fn scan_file(path: String) -> Result<serde_json::Value, String> {
    let out = run_capture("guardian.py", &["--scan", &path])?;
    serde_json::from_str(&out).map_err(|e| format!("bad scan output: {e} :: {out}"))
}

#[tauri::command]
pub fn ask_llm(prompt: String) -> Result<String, String> {
    run_capture("llm_bridge.py", &["--prompt", &prompt])
}

/// Offline text-to-image via local ComfyUI (bridges ai-core/image_bridge.py).
/// Fails soft with setup instructions when ComfyUI is not running.
#[tauri::command]
pub fn generate_image(prompt: String) -> Result<serde_json::Value, String> {
    let out = run_capture("image_bridge.py", &["--prompt", &prompt])?;
    serde_json::from_str(&out).map_err(|e| format!("bad image bridge output: {e} :: {out}"))
}

#[tauri::command]
pub fn launch_emulator(
    image: Option<String>,
    state: State<AppState>,
) -> Result<EmulatorStatus, String> {
    let mut guard = state.emulator_child.lock().map_err(|e| e.to_string())?;
    if let Some(c) = guard.as_mut() {
        if c.try_wait().ok().flatten().is_none() {
            return Ok(EmulatorStatus { running: true, image, pid: Some(c.id()) });
        }
    }
    let img = image.unwrap_or_else(|| "emulator/images/android-x86.iso".into());
    let child = python_cmd("emulator_controller.py")
        .args(["--image", &img])
        .spawn()
        .map_err(|e| format!("failed to launch emulator: {e}"))?;
    let pid = child.id();
    *guard = Some(child);
    Ok(EmulatorStatus { running: true, image: Some(img), pid: Some(pid) })
}

#[tauri::command]
pub fn stop_emulator(state: State<AppState>) -> EmulatorStatus {
    if let Ok(mut guard) = state.emulator_child.lock() {
        if let Some(mut c) = guard.take() {
            let _ = c.kill();
        }
    }
    EmulatorStatus { running: false, image: None, pid: None }
}

// ---------- Token earn model (bridges ai-core/token_ledger.py) ----------

#[tauri::command]
pub fn get_token_balance() -> Result<serde_json::Value, String> {
    let out = run_capture("token_ledger.py", &["--balance"])?;
    serde_json::from_str(&out).map_err(|e| format!("bad ledger output: {e}"))
}

/// story=+50, dream=+150, skill=+100.
/// Content NEVER leaves the PC: only a locally generated reference hash
/// is written to the dual append-only ledger.
#[tauri::command]
pub fn earn_tokens(kind: String) -> Result<serde_json::Value, String> {
    let k = kind.to_lowercase();
    if !matches!(k.as_str(), "story" | "dream" | "skill") {
        return Err("unknown earn kind: expected story | dream | skill".into());
    }
    let seed = format!("{:?}::{}::{}", SystemTime::now(), std::process::id(), k);
    let ref_hash: String = Sha256::digest(seed.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    let out = run_capture("token_ledger.py", &["--earn", &k, &ref_hash])?;
    serde_json::from_str(&out).map_err(|e| format!("bad earn output: {e}"))
}
