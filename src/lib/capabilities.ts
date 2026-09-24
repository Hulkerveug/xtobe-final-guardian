export type Capabilities = {
  core: boolean;
  ollama: boolean;
  qemu: boolean;
  comfyui: boolean;
  token_ledger: boolean;
  license_server: boolean;
  version: string;
};

export async function getCapabilities(): Promise<Capabilities> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<Capabilities>("get_capabilities");
}
