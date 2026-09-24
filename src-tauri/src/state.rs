use std::process::Child;
use std::sync::Mutex;

/// Shared application state: handles to the Python AI sidecar and the
/// QEMU emulator child process so we can stop them from the UI.
pub struct AppState {
    pub guardian_child: Mutex<Option<Child>>,
    pub emulator_child: Mutex<Option<Child>>,
}
