import { useState } from "react";

type Tone = "safe" | "neon" | "warn";

interface Platform {
  name: string;
  tech: string;
  status: string;
  tone: Tone;
  icon: string;
  /** node position in the hub diagram (viewBox 640x300) */
  x: number;
  y: number;
}

const CENTER = { x: 320, y: 150 };

const PLATFORMS: Platform[] = [
  { name: "Web App", tech: "React", status: "LIVE", tone: "safe", icon: "🌐", x: 110, y: 58 },
  { name: "Desktop Guardian", tech: "Tauri · Win/Mac/Linux", status: "EMULATION VIEW", tone: "neon", icon: "🖥️", x: 320, y: 38 },
  { name: "Mobile", tech: "iOS & Android", status: "LIVE", tone: "safe", icon: "📱", x: 530, y: 58 },
  { name: "WhatsApp Normal Path", tech: "QR Verified", status: "COMPLIANT", tone: "safe", icon: "💬", x: 110, y: 242 },
  { name: "WhatsApp Business API", tech: "Template + 24h free-text", status: "READY", tone: "warn", icon: "🏢", x: 320, y: 262 },
  { name: "SIM Card Guardian", tech: "Physical SIM + Emulation Rack", status: "SIM-SECURED", tone: "neon", icon: "🔐", x: 530, y: 242 },
];

const TONE_TEXT: Record<Tone, string> = {
  safe: "text-safe border-safe/40 bg-safe/10",
  neon: "text-neon border-neon/40 bg-neon/10",
  warn: "text-warn border-warn/40 bg-warn/10",
};

const TONE_HEX: Record<Tone, string> = {
  safe: "#34d399",
  neon: "#22d3ee",
  warn: "#fbbf24",
};

const STEPS = [
  { n: "1", title: "Insert SIM / Verify", body: "Physical SIM or QR pairs the device to your Guardian identity." },
  { n: "2", title: "Guardian Emulation Loads", body: "The sandboxed emulation layer boots and locks the session." },
  { n: "3", title: "Chat Anywhere", body: "One encrypted inbox — desktop, mobile, watch, WhatsApp." },
];

export default function WorksEverywhere() {
  const [hover, setHover] = useState<number | null>(null);

  const openDemo = () => {
    document.getElementById("emulator-lab")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="panel flex flex-col gap-4">
      {/* header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="panel-title">
            XTOBE <span className="text-slate-100">WORKS EVERYWHERE</span>
          </h2>
          <p className="text-[11px] text-slate-500">One System. Every Platform. SIM-Secured.</p>
        </div>
        <button className="btn-neon" onClick={openDemo}>
          VIEW LIVE DEMO — EMULATION VIEW
        </button>
      </div>

      {/* hub diagram */}
      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2">
        <svg viewBox="0 0 640 300" className="w-full h-56 select-none">
          {/* encrypted links */}
          {PLATFORMS.map((p, i) => (
            <line
              key={`l${i}`}
              x1={CENTER.x}
              y1={CENTER.y}
              x2={p.x}
              y2={p.y}
              stroke={hover === i ? TONE_HEX[p.tone] : "#1e293b"}
              strokeWidth={hover === i ? 2 : 1}
              strokeDasharray="5 4"
            />
          ))}
          {/* core server */}
          <g>
            <rect x={CENTER.x - 62} y={CENTER.y - 24} width="124" height="48" rx="10"
              fill="#0f172a" stroke="#22d3ee" strokeWidth="1.5" />
            <text x={CENTER.x} y={CENTER.y - 4} textAnchor="middle" fill="#22d3ee" fontSize="12" fontWeight="700">
              XTOBE-2 CORE
            </text>
            <text x={CENTER.x} y={CENTER.y + 12} textAnchor="middle" fill="#64748b" fontSize="9">
              🔒 encrypted hub
            </text>
          </g>
          {/* satellites */}
          {PLATFORMS.map((p, i) => (
            <g
              key={`n${i}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              className="cursor-pointer"
              opacity={hover === null || hover === i ? 1 : 0.45}
            >
              <rect x={p.x - 58} y={p.y - 16} width="116" height="32" rx="8"
                fill="#0f172a" stroke={TONE_HEX[p.tone]} strokeWidth={hover === i ? 2 : 1} />
              <text x={p.x} y={p.y - 2} textAnchor="middle" fill="#e2e8f0" fontSize="9.5" fontWeight="600">
                {p.icon} {p.name.length > 18 ? p.name.slice(0, 17) + "…" : p.name}
              </text>
              <text x={p.x} y={p.y + 10} textAnchor="middle" fill={TONE_HEX[p.tone]} fontSize="7.5">
                {p.status}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* platform cards */}
      <div className="grid grid-cols-3 gap-3">
        {PLATFORMS.map((p, i) => (
          <div
            key={p.name}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            className={`rounded-lg border border-slate-800 bg-slate-950/60 p-3 transition ${
              hover === i ? "border-slate-600" : ""
            }`}
          >
            <div className="text-lg">{p.icon}</div>
            <div className="text-xs font-semibold text-slate-200 mt-1">{p.name}</div>
            <div className="text-[10px] text-slate-500">{p.tech}</div>
            <span className={`mt-2 inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wide ${TONE_TEXT[p.tone]}`}>
              {p.status}
            </span>
          </div>
        ))}
      </div>

      {/* how it works */}
      <div className="grid grid-cols-3 gap-3">
        {STEPS.map((s) => (
          <div key={s.n} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex gap-3">
            <div className="text-neon text-lg font-bold">{s.n}</div>
            <div>
              <div className="text-xs font-semibold text-slate-200">{s.title}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{s.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
