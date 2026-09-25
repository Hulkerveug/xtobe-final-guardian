import type { GuardianHost } from "./GuardianHost";

export const BrowserHost: GuardianHost = {
  getSystemStats: async () => ({ cpu_usage: 0, mem_used_gb: 0, mem_total_gb: 0, process_count: 0, guardian_active: false, available: false, source: "browser" }),
  listProcesses: async () => [],
  getTokenBalance: async () => ({ balance: 0, free_inference_calls: 0 }),
  startAiGuardian: async () => { throw new Error("Guardian host is unavailable in browser preview"); },
};
