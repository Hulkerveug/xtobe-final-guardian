import type { GuardianHost } from "./GuardianHost";

type ElectronBridge = {
  getSystemStats?: () => Promise<unknown>;
  listProcesses?: () => Promise<unknown>;
  getTokenBalance?: () => Promise<unknown>;
  startAiGuardian?: () => Promise<unknown>;
};

declare global {
  interface Window { guardianBridge?: ElectronBridge; }
}

export const ElectronHost: GuardianHost = {
  getSystemStats: async () => {
    const result = await window.guardianBridge?.getSystemStats?.();
    if (!result || typeof result !== "object") throw new Error("Electron system bridge unavailable");
    return { ...(result as object), source: "electron", available: true } as Awaited<ReturnType<GuardianHost["getSystemStats"]>>;
  },
  listProcesses: async () => (await window.guardianBridge?.listProcesses?.() ?? []) as Awaited<ReturnType<GuardianHost["listProcesses"]>>,
  getTokenBalance: async () => (await window.guardianBridge?.getTokenBalance?.() ?? { balance: 0, free_inference_calls: 0 }) as Awaited<ReturnType<GuardianHost["getTokenBalance"]>>,
  startAiGuardian: async () => { if (!window.guardianBridge?.startAiGuardian) throw new Error("Electron Guardian bridge unavailable"); await window.guardianBridge.startAiGuardian(); },
};
