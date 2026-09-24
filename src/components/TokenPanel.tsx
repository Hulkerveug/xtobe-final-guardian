import { useEffect, useState } from "react";
import { earnTokens, getTokenBalance } from "../api";
import type { TokenBalance } from "../types";

const EARNERS: { kind: "story" | "dream" | "skill"; label: string; delta: number; hint: string }[] = [
  { kind: "story", label: "SHARE STORY", delta: 50, hint: "anonymized lived event" },
  { kind: "dream", label: "SHARE DREAM", delta: 150, hint: "feelings stay in feelings.json — local only" },
  { kind: "skill", label: "SHARE SKILL", delta: 100, hint: "reproducible workflow" },
];

export default function TokenPanel() {
  const [bal, setBal] = useState<TokenBalance | null>(null);
  const [flash, setFlash] = useState("");

  const refresh = () => getTokenBalance().then(setBal).catch(() => {});
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, []);

  const earn = async (kind: "story" | "dream" | "skill") => {
    try {
      const r = await earnTokens(kind);
      setFlash(`+${r.delta} TOKENS EARNED`);
      setBal((b) => b && { ...b, balance: r.balance_after });
      refresh();
      setTimeout(() => setFlash(""), 2500);
    } catch (e) {
      setFlash(`earn error: ${String(e)}`);
    }
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-title">
        <span className="text-warn">◈</span> TOKEN CORE
        <span className="ml-auto text-[10px] text-slate-500">1 token = 10 inference calls · local only</span>
      </div>
      <div className="flex items-center gap-6">
        <div>
          <div className="text-[10px] text-slate-500">BALANCE</div>
          <div className="text-3xl font-bold text-warn">{bal ? bal.balance : "—"}</div>
          <div className="text-[10px] text-slate-500">
            {bal ? `${bal.free_inference_calls} free AI calls` : "ledger offline"}
          </div>
        </div>
        {flash && <div className="text-safe text-xs animate-pulse">{flash}</div>}
        <div className="ml-auto flex gap-2">
          {EARNERS.map((e) => (
            <button
              key={e.kind}
              className="btn-neon"
              title={e.hint}
              onClick={() => earn(e.kind)}
            >
              {e.label} +{e.delta}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-2 text-[10px] text-slate-600">
        Earn compute by contributing lived experience. Content never leaves this PC — only a
        reference hash is written to the dual append-only ledger. Console: type{" "}
        <span className="text-neon">share story</span> in AI Core.
      </p>
    </div>
  );
}
