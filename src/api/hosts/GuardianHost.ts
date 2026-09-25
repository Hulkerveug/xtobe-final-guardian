import type { ProcessInfo, SystemStats, TokenBalance } from "../../types";

export interface GuardianHost {
  getSystemStats(): Promise<SystemStats>;
  listProcesses(): Promise<ProcessInfo[]>;
  getTokenBalance(): Promise<TokenBalance>;
  startAiGuardian(): Promise<void>;
}
