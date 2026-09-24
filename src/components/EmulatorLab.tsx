import { useState } from "react";
import type { EmulatorStatus } from "../types";
import { launchEmulator, stopEmulator } from "../api";

export default function EmulatorLab() {
  const [status, setStatus] = useState<EmulatorStatus>({ running: false, image: null, pid: null });
  const [image, setImage] = useState("emulator/images/android-x86.iso");
  const [log, setLog] = useState<string[]>([
    "Sandbox idle. Drop an ISO/APK image path and boot the QEMU sandbox.",
    "Policy: untrusted installers run HERE first — promoted to host only if clean.",
  ]);

  const push = (line: string) =>
    setLog((l) => [...l.slice(-60), `[${new Date().toLocaleTimeString()}] ${line}`]);

  const boot = async () => {
    push(`Booting sandbox: ${image}`);
    try {
      const s = await launchEmulator(image);
      setStatus(s);
      push(s.running ? `Sandbox running (pid ${s.pid})` : "Sandbox failed to start — check QEMU path.");
    } catch (e) {
      push(`launch error: ${String(e)}`);
    }
  };

  const stop = async () => {
    const s = await stopEmulator();
    setStatus(s);
    push("Sandbox terminated. Image state discarded.");
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-title">
        ⬡ EMULATOR LAB
        <span className={`ml-auto text-[10px] ${status.running ? "text-safe" : "text-slate-500"}`}>
          {status.running ? `RUNNING · pid ${status.pid}` : "STOPPED"}
        </span>
      </div>
      <div className="flex gap-2 mb-2">
        <input
          className="flex-1 bg-void border border-edge rounded-md px-2 py-1.5 text-xs outline-none focus:border-neon/60"
          value={image}
          onChange={(e) => setImage(e.target.value)}
          placeholder="emulator/images/android-x86.iso"
        />
        {status.running ? (
          <button className="btn-danger" onClick={stop}>STOP</button>
        ) : (
          <button className="btn-neon" onClick={boot}>BOOT SANDBOX</button>
        )}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto bg-void border border-edge rounded-md p-2 text-[10px] text-slate-400 space-y-0.5">
        {log.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  );
}
