export interface SystemStats {
  cpu_usage: number;
  mem_used_gb: number;
  mem_total_gb: number;
  process_count: number;
  guardian_active: boolean;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  exe: string | null;
  cpu: number;
  mem_mb: number;
  risk: "safe" | "warn" | "danger";
}

export interface ThreatEvent {
  timestamp: string;
  pid: number;
  name: string;
  path: string;
  reason: string;
  severity: "low" | "medium" | "high" | "critical";
}

export interface ScanResult {
  path: string;
  sha256: string;
  verdict: "clean" | "suspicious" | "malicious";
  rules_hit: string[];
}

export interface EmulatorStatus {
  running: boolean;
  image: string | null;
  pid: number | null;
}

export interface LicenseStatus {
  valid: boolean;
  source: "server" | "offline-grace" | "none";
  offline_days_left: number;
}

export interface TokenBalance {
  balance: number;
  free_inference_calls: number;
}

export interface Entitlement {
  mode: "trial" | "lifetime" | "locked";
  days_left: number;    // -1 when lifetime
  actions_left: number; // -1 when lifetime
}

export type MemoryKind = "build" | "learn" | "security" | "user";

export interface MemoryEntry { timestamp: string; type: MemoryKind; message: string; }
export interface TaskRecord { id: string; command: string; status: "queued" | "running" | "complete" | "failed"; createdAt: string; }
