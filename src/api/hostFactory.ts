import { BrowserHost } from "./hosts/BrowserHost";
import { ElectronHost } from "./hosts/ElectronHost";
import { TauriHost } from "./hosts/TauriHost";
import type { GuardianHost } from "./hosts/GuardianHost";

export function getHost(): GuardianHost {
  if ("__TAURI__" in window) return TauriHost;
  if (window.guardianBridge) return ElectronHost;
  return BrowserHost;
}
