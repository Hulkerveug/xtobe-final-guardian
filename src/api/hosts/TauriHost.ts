import { getSystemStats, listProcesses, getTokenBalance, startAiGuardian } from "../../api";
import type { GuardianHost } from "./GuardianHost";

export const TauriHost: GuardianHost = {
  getSystemStats: async () => ({ ...(await getSystemStats()), source: "tauri", available: true }),
  listProcesses,
  getTokenBalance,
  startAiGuardian: async () => { await startAiGuardian(); },
};
