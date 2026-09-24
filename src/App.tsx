import { useEffect, useState } from "react";
import type { SystemStats, Entitlement } from "./types";
import { getSystemStats, startAiGuardian, getEntitlement } from "./api";
import { checkForUpdates } from "./updater";
import AiCorePanel from "./components/AiCorePanel";
import ThreatMatrix from "./components/ThreatMatrix";
import EmulatorLab from "./components/EmulatorLab";
import InstallerBuilder from "./components/InstallerBuilder";
import Paywall from "./components/Paywall";
import TokenPanel from "./components/TokenPanel";
import WorksEverywhere from "./components/WorksEverywhere";
import CinemaMode from "./components/CinemaMode";

export default function App() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [booting, setBooting] = useState(false);
  const [updateStatus, setUpdateStatus] = useState("checking updates…");
  const [ent, setEnt] = useState<Entitlement | null>(null);
  const [cinema, setCinema] = useState(false);

  useEffect(() => {
    const tick = () => {
      getSystemStats().then(setStats).catch(() => {});
      getEntitlement().then(setEnt).catch(() => {});
    };
    tick();
    const id = setInterval(tick, 2000);
    checkForUpdates().then(setUpdateStatus);
    return () => clearInterval(id);
  }, []);

  const bootGuardian = async () => {
    setBooting(true);
    try {
      await startAiGuardian();
    } finally {
      setBooting(false);
    }
  };

  return (
    <div className="min-h-screen p-4 flex flex-col gap-4">
      <header className="panel flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-neon tracking-wide">
            XTOBE <span className="text-slate-100">FINAL GUARDIAN</span>
          </h1>
          <p className="text-[11px] text-slate-500">
            Offline AI defense core · sandboxed emulator · real-time threat matrix
          </p>
          <p className="text-[10px] text-slate-600 mt-0.5">{updateStatus}</p>
        </div>
        <div className="flex items-center gap-6 text-xs">
          {ent?.mode === "trial" && (
            <div className="rounded-md border border-warn/40 bg-warn/10 px-2 py-1 text-warn">
              TRIAL · {ent.days_left}d · {ent.actions_left} actions
            </div>
          )}
          {ent?.mode === "lifetime" && (
            <div className="rounded-md border border-safe/40 bg-safe/10 px-2 py-1 text-safe">
              LIFETIME ✓
            </div>
          )}
          <Stat label="CPU" value={stats ? `${stats.cpu_usage.toFixed(1)}%` : "—"} />
          <Stat
            label="MEM"
            value={stats ? `${stats.mem_used_gb.toFixed(1)}/${stats.mem_total_gb.toFixed(0)} GB` : "—"}
          />
          <Stat label="PROCS" value={stats ? String(stats.process_count) : "—"} />
          <button className="btn-ghost" onClick={() => setCinema(true)}>
            🎬 CINEMA
          </button>
          <button className="btn-neon" onClick={bootGuardian} disabled={booting}>
            {stats?.guardian_active ? "● GUARDIAN LIVE" : booting ? "BOOTING…" : "ACTIVATE GUARDIAN"}
          </button>
        </div>
      </header>

      <main className="grid grid-cols-12 gap-4 flex-1 min-h-0">
        <section className="col-span-5 min-h-0">
          <AiCorePanel guardianActive={stats?.guardian_active ?? false} />
        </section>
        <section className="col-span-7 min-h-0">
          <ThreatMatrix />
        </section>
        <section id="emulator-lab" className="col-span-7 min-h-0">
          <EmulatorLab />
        </section>
        <section className="col-span-5 min-h-0">
          <InstallerBuilder />
        </section>
        <section className="col-span-12 min-h-0">
          <TokenPanel />
        </section>
        <section className="col-span-12 min-h-0">
          <WorksEverywhere />
        </section>
      </main>

      {ent?.mode === "locked" && (
        <Paywall onActivated={() => getEntitlement().then(setEnt).catch(() => {})} />
      )}
      {cinema && <CinemaMode onExit={() => setCinema(false)} />}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className="text-neon">{value}</div>
    </div>
  );
}
