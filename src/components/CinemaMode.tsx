import { useEffect, useRef, useState } from "react";

/** Cinematic auto-play demo: the real events of a Guardian threat interception,
 *  presented like a movie. Press ESC or click SKIP to exit. */

interface Act {
  title: string;
  color: string; // tailwind text class
  lines: string[];
  typewriter?: boolean; // type lines char-by-char
  holdMs: number; // pause after act completes
}

const ACTS: Act[] = [
  {
    title: "SYSTEM BOOT",
    color: "text-neon",
    holdMs: 2200,
    lines: [
      "> XTOBE FINAL GUARDIAN v2.0",
      "> lockdown check ............ 12/12 PASS",
      "> guard failures ............ 0",
      "> yara engine ............... 4 rules hot-loaded",
      "> offline AI core ........... llama3.1:8b READY",
      "> token ledger .............. 550 XTOK",
      "> daemon .................... WATCHING ALL PROCESSES",
    ],
  },
  {
    title: "⚠ THREAT DETECTED",
    color: "text-danger",
    holdMs: 2600,
    lines: [
      '> new process: "invoice.pdf.exe"',
      "> path: C:\\Users\\...\\AppData\\Local\\Temp\\",
      "> heuristic: TEMP-DIR EXECUTION ......... HIGH",
      "> heuristic: DOUBLE EXTENSION MASQUERADE . CRITICAL",
      "> YARA match: Xtobe_Test_Payload ........ CRITICAL",
      "",
      '>> verdict: "malicious"',
    ],
  },
  {
    title: "AI VERDICT — OFFLINE, NO CLOUD",
    color: "text-safe",
    typewriter: true,
    holdMs: 2400,
    lines: [
      "This file is dangerous: it disguises itself as a PDF invoice,",
      "executes from a temporary directory, and matches a known",
      "malware signature. Recommendation: terminate immediately and",
      "quarantine inside the Guardian emulation sandbox.",
    ],
  },
  {
    title: "CONTAINMENT",
    color: "text-warn",
    holdMs: 2200,
    lines: [
      "> process terminated ........ OK",
      "> file hashed ............... sha256 37d76a55…",
      "> threat logged ............. threats.json",
      "> inference cost ............ -1 XTOK",
      "> ledger balance ............ 549 XTOK",
      "",
      ">> host integrity: UNTOUCHED",
    ],
  },
  {
    title: "XTOBE GUARDIAN",
    color: "text-neon",
    holdMs: 999999,
    lines: [
      "One System. Every Platform. SIM-Secured.",
      "",
      "your PC. your AI. your rules.",
      "",
      "— press ESC to return to command center —",
    ],
  },
];

export default function CinemaMode({ onExit }: { onExit: () => void }) {
  const [actIdx, setActIdx] = useState(0);
  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const [typed, setTyped] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const act = ACTS[actIdx];

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onExit();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onExit]);

  useEffect(() => {
    setVisibleLines([]);
    setTyped("");
    let cancelled = false;

    if (act.typewriter) {
      // typewriter: type all lines as one block
      const full = act.lines.join("\n");
      let i = 0;
      const tick = () => {
        if (cancelled) return;
        i += 1;
        setTyped(full.slice(0, i));
        if (i < full.length) timer.current = setTimeout(tick, 28);
        else timer.current = setTimeout(next, act.holdMs);
      };
      tick();
    } else {
      // line-by-line reveal
      let i = 0;
      const tick = () => {
        if (cancelled) return;
        if (i < act.lines.length) {
          setVisibleLines((v) => [...v, act.lines[i]]);
          i += 1;
          timer.current = setTimeout(tick, 420);
        } else {
          timer.current = setTimeout(next, act.holdMs);
        }
      };
      tick();
    }
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actIdx]);

  const next = () => {
    if (actIdx < ACTS.length - 1) setActIdx(actIdx + 1);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col items-center justify-center font-mono select-none">
      {/* ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-neon/5 rounded-full blur-3xl pointer-events-none" />
      {/* scanlines */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.06]"
        style={{
          backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, #22d3ee 3px)",
        }}
      />

      {/* act counter */}
      <div className="absolute top-6 left-8 text-[10px] tracking-[0.3em] text-slate-600">
        ACT {actIdx + 1} / {ACTS.length}
      </div>
      <button
        onClick={onExit}
        className="absolute top-5 right-8 text-[10px] tracking-[0.3em] text-slate-500 hover:text-neon transition"
      >
        SKIP ✕
      </button>

      <div className="w-[640px] max-w-[90vw]">
        <div className={`text-sm tracking-[0.4em] mb-6 ${act.color} animate-pulse`}>{act.title}</div>
        <div className="min-h-[220px] text-[13px] leading-6 text-slate-300 whitespace-pre-wrap">
          {act.typewriter ? (
            <>
              {typed}
              <span className="animate-pulse text-neon">▌</span>
            </>
          ) : (
            visibleLines.map((l, i) => (
              <div key={i} className={l.startsWith(">>") ? `${act.color} font-bold mt-2` : ""}>
                {l || "\u00A0"}
              </div>
            ))
          )}
        </div>
        <div className="mt-4 h-px bg-gradient-to-r from-transparent via-neon/40 to-transparent" />
        <div
          className="mt-3 text-[10px] tracking-[0.25em] text-slate-600 cursor-pointer hover:text-slate-300 transition"
          onClick={next}
        >
          {actIdx < ACTS.length - 1 ? "▶ CLICK TO CONTINUE" : ""}
        </div>
      </div>
    </div>
  );
}
