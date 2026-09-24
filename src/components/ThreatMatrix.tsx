import { useEffect, useState } from "react";
import type { ProcessInfo } from "../types";
import { listProcesses, killProcess } from "../api";

export default function ThreatMatrix() {
  const [procs, setProcs] = useState<ProcessInfo[]>([]);
  const [filter, setFilter] = useState("");

  const refresh = () => listProcesses().then(setProcs).catch(() => {});

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, []);

  const shown = procs
    .filter((p) => p.name.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => riskRank(b.risk) - riskRank(a.risk) || b.cpu - a.cpu)
    .slice(0, 40);

  const flagged = procs.filter((p) => p.risk !== "safe").length;

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-title">
        ⚠ THREAT MATRIX
        <span className={`ml-auto text-[10px] ${flagged ? "text-danger" : "text-safe"}`}>
          {flagged ? `${flagged} FLAGGED` : "ALL CLEAR"}
        </span>
      </div>
      <input
        className="mb-2 bg-void border border-edge rounded-md px-2 py-1 text-xs outline-none focus:border-neon/60"
        placeholder="filter processes…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        <table className="w-full text-[11px]">
          <thead className="text-slate-500 sticky top-0 bg-panel">
            <tr className="text-left">
              <th className="py-1">PID</th>
              <th>NAME</th>
              <th className="text-right">CPU%</th>
              <th className="text-right">MEM MB</th>
              <th>RISK</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((p) => (
              <tr key={p.pid} className="border-t border-edge/50 hover:bg-edge/20">
                <td className="py-1 text-slate-500">{p.pid}</td>
                <td className="truncate max-w-[180px]" title={p.exe ?? p.name}>
                  {p.name}
                </td>
                <td className="text-right">{p.cpu.toFixed(1)}</td>
                <td className="text-right">{p.mem_mb.toFixed(0)}</td>
                <td className={`risk-${p.risk} font-semibold`}>{p.risk.toUpperCase()}</td>
                <td className="text-right">
                  {p.risk === "danger" && (
                    <button className="btn-danger" onClick={() => killProcess(p.pid).then(refresh)}>
                      KILL
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function riskRank(r: ProcessInfo["risk"]) {
  return r === "danger" ? 2 : r === "warn" ? 1 : 0;
}
