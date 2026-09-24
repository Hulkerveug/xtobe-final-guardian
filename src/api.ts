import { invoke } from "@tauri-apps/api/core";
import type {
  SystemStats,
  ProcessInfo,
  ScanResult,
  EmulatorStatus,
  LicenseStatus,
  Entitlement,
  TokenBalance,
} from "./types";

export const getSystemStats = () => invoke<SystemStats>("get_system_stats");
export const listProcesses = () => invoke<ProcessInfo[]>("list_processes");
export const killProcess = (pid: number) =>
  invoke<boolean>("kill_process", { pid });
export const startAiGuardian = () => invoke<string>("start_ai_guardian");
export const scanFile = (path: string) =>
  invoke<ScanResult>("scan_file", { path });
export const launchEmulator = (image?: string) =>
  invoke<EmulatorStatus>("launch_emulator", { image: image ?? null });
export const stopEmulator = () => invoke<EmulatorStatus>("stop_emulator");
export const askLlm = (prompt: string) =>
  invoke<string>("ask_llm", { prompt });
export const checkLicense = (key: string) =>
  invoke<LicenseStatus>("check_license", { key });
export const getEntitlement = () => invoke<Entitlement>("get_entitlement");
export const recordAction = () => invoke<Entitlement>("record_action");
export const getTokenBalance = () => invoke<TokenBalance>("get_token_balance");
export const earnTokens = (kind: "story" | "dream" | "skill") =>
  invoke<{ kind: string; delta: number; balance_after: number }>("earn_tokens", { kind });
