import { check } from "@tauri-apps/plugin-updater";

/**
 * Silent auto-update check against https://xtobe.app/api/updates/...
 * Downloads + installs in the background; user restarts to apply.
 * Fails soft when offline or before the signing pubkey is configured.
 */
export async function checkForUpdates(): Promise<string> {
  try {
    const update = await check();
    if (!update) return "v2.0.0 · up to date";
    await update.downloadAndInstall();
    return `v${update.version} installed · restart to apply`;
  } catch {
    return "v2.0.0 · offline mode";
  }
}
