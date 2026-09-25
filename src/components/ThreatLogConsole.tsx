import { useEffect, useState } from "react";
import { listProcesses } from "../api";
import type { ProcessInfo } from "../types";

type RiskStatus = "MONITORED" | "REVIEW" | "REQUIRES ATTENTION";

type TelemetryEntry = {
  key: string;
  timestamp: string;
  process: ProcessInfo;
  status: RiskStatus;
};

const statusFor = (process: ProcessInfo): RiskStatus => {
  if (process.risk === "danger" || process.cpu >= 80 || process.mem_mb >= 1024) return "REQUIRES ATTENTION";
  if (process.risk === "warn" || process.cpu >= 40 || process.mem_mb >= 512) return "REVIEW";
  return "MONITORED";
};

export default function ThreatLogConsole() {
  const [entries, setEntries] = useState<TelemetryEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "live" | "error">("loading");

  useEffect(() => {
    let active = true;
    const refresh = () => {
      listProcesses()
        .then((processes) => {
          if (!active) return;
          setEntries(processes.slice(0, 10).map((process) => ({
            key: `${process.pid}-${process.name}`,
            timestamp: new Date().toLocaleTimeString(),
            process,
            status: statusFor(process),
          })));
          setStatus("live");
        })
        .catch(() => active && setStatus("error"));
    };
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  return <section className="panel" aria-live="polite">
    <div className="panel-title">◉ PROCESS TELEMETRY // LOCAL READ-ONLY <span className="ml-auto text-[10px] text-slate-500">3S POLL</span></div>
    {status === "error" && <p className="text-xs text-danger">[TELEMETRY ERROR] Local process data is unavailable.</p>}
    {status === "loading" && entries.length === 0 && <p className="text-xs text-slate-500">Querying local process tree…</p>}
    {status !== "error" && <div className="max-h-56 space-y-1 overflow-y-auto">
      {entries.map((entry) => <div key={entry.key} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-t border-edge/50 py-1 text-[11px]">
        <span className="text-slate-600">{entry.timestamp}</span>
        <span className="truncate">{entry.process.name} <span className="text-slate-600">PID {entry.process.pid} · CPU {entry.process.cpu.toFixed(1)}% · RAM {entry.process.mem_mb.toFixed(0)} MB</span></span>
        <span className={entry.status === "REQUIRES ATTENTION" ? "text-danger" : entry.status === "REVIEW" ? "text-warn" : "text-safe"}>{entry.status}</span>
      </div>)}
    </div>}
  </section>;
}
