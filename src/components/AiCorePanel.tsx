import { useState } from "react";
import { askLlm, scanFile, recordAction, earnTokens } from "../api";

interface Msg {
  role: "you" | "xtobe";
  text: string;
}

export default function AiCorePanel({ guardianActive }: { guardianActive: boolean }) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "xtobe", text: "AI Core idle. Activate the Guardian, then talk to me — fully offline via Ollama." },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [scanPath, setScanPath] = useState("");
  const [scanOut, setScanOut] = useState("");

  const send = async () => {
    const prompt = input.trim();
    if (!prompt) return;
    const ent = await recordAction().catch(() => null);
    if (ent?.mode === "locked") {
      setMsgs((m) => [...m, { role: "xtobe", text: "Trial exhausted — unlock Lifetime to keep going." }]);
      return;
    }
    setMsgs((m) => [...m, { role: "you", text: prompt }]);

    // Console earn commands: "share story" / "share dream" / "share skill"
    const earnMatch = /^share\s+(story|dream|skill)$/i.exec(prompt);
    if (earnMatch) {
      try {
        const r = await earnTokens(earnMatch[1].toLowerCase() as "story" | "dream" | "skill");
        setMsgs((m) => [...m, { role: "xtobe", text: `+${r.delta} tokens earned (${r.kind}). Balance: ${r.balance_after}.` }]);
      } catch (e) {
        setMsgs((m) => [...m, { role: "xtobe", text: `earn error: ${String(e)}` }]);
      }
      return;
    }
    setInput("");
    setThinking(true);
    try {
      const reply = await askLlm(prompt);
      setMsgs((m) => [...m, { role: "xtobe", text: reply }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "xtobe", text: `LLM bridge error: ${String(e)}` }]);
    } finally {
      setThinking(false);
    }
  };

  const runScan = async () => {
    if (!scanPath.trim()) return;
    const ent = await recordAction().catch(() => null);
    if (ent?.mode === "locked") {
      setScanOut("Trial exhausted — unlock Lifetime to keep scanning.");
      return;
    }
    setScanOut("Scanning…");
    try {
      const r = await scanFile(scanPath.trim());
      setScanOut(
        `verdict: ${r.verdict.toUpperCase()}\nsha256: ${r.sha256}\nrules: ${r.rules_hit.join(", ") || "none"}`
      );
    } catch (e) {
      setScanOut(`scan error: ${String(e)}`);
    }
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-title">
        <span className={guardianActive ? "text-safe" : "text-warn"}>◉</span> AI CORE
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 text-xs pr-1">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "you" ? "text-right" : ""}>
            <span
              className={`inline-block px-2 py-1 rounded-md max-w-[90%] whitespace-pre-wrap ${
                m.role === "you" ? "bg-edge/60 text-slate-200" : "bg-neon/10 text-neon"
              }`}
            >
              {m.text}
            </span>
          </div>
        ))}
        {thinking && <div className="text-neon/60 text-xs">Xtobe is thinking…</div>}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="flex-1 bg-void border border-edge rounded-md px-2 py-1.5 text-xs outline-none focus:border-neon/60"
          placeholder='"Xtobe, scan system" — or ask anything…'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn-neon" onClick={send} disabled={thinking}>
          SEND
        </button>
      </div>
      <div className="mt-3 border-t border-edge pt-3">
        <div className="text-[10px] text-slate-500 mb-1">DEEP FILE SCAN (YARA + hash)</div>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-void border border-edge rounded-md px-2 py-1.5 text-xs outline-none focus:border-neon/60"
            placeholder="C:\path\to\file.exe"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
          />
          <button className="btn" onClick={runScan}>SCAN</button>
        </div>
        {scanOut && <pre className="mt-2 text-[10px] text-slate-400 whitespace-pre-wrap">{scanOut}</pre>}
      </div>
    </div>
  );
}
