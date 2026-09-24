import { useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { checkLicense } from "../api";

const BUY_URL = "https://xtobe.app/#pricing"; // Paddle checkout lives on the landing

interface Props {
  onActivated: () => void;
}

/**
 * Full-screen lock overlay shown when the 7-day / 100-action trial ends.
 * Buy -> Paddle (Merchant of Record) on the landing page.
 * Activate -> paste the XTOBE- key from the purchase email.
 */
export default function Paywall({ onActivated }: Props) {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const activate = async () => {
    if (!key.trim()) return;
    setBusy(true);
    setMsg("");
    try {
      const st = await checkLicense(key.trim());
      if (st.valid) {
        onActivated();
      } else {
        setMsg("That key was not accepted. Check the purchase email and try again.");
      }
    } catch {
      setMsg("Could not reach the license server. Check your connection.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/95 backdrop-blur">
      <div className="w-full max-w-md rounded-2xl border border-cyan-500/30 bg-slate-900 p-8 shadow-2xl shadow-cyan-500/10">
        <div className="mb-1 text-xs font-bold tracking-[0.3em] text-cyan-400">XTOBE FINAL GUARDIAN</div>
        <h2 className="mb-2 text-2xl font-bold text-white">Your free trial has ended</h2>
        <p className="mb-4 text-sm text-slate-400">
          You proved it works: <span className="text-emerald-400">Lockdown 12/12 PASS</span>, Guard 0 failures.
          Keep your Guardian alive forever with a one-time payment.
        </p>

        <button
          onClick={() => openUrl(BUY_URL)}
          className="mb-3 w-full rounded-xl bg-cyan-500 py-3 text-center font-bold text-slate-950 transition hover:bg-cyan-400"
        >
          Buy Lifetime License — $29
        </button>
        <p className="mb-5 text-center text-xs text-slate-500">
          Secure checkout by Paddle — VAT/tax handled worldwide, pay in your currency
        </p>

        <div className="mb-2 text-xs font-semibold tracking-widest text-slate-400">ALREADY PURCHASED? PASTE YOUR KEY</div>
        <input
          value={key}
          onChange={(e) => setKey(e.target.value.toUpperCase())}
          placeholder="XTOBE-XXXX-XXXX-XXXX-XXXX"
          className="mb-2 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-sm text-cyan-300 outline-none focus:border-cyan-500"
        />
        {msg && <p className="mb-2 text-xs text-rose-400">{msg}</p>}
        <button
          onClick={activate}
          disabled={busy}
          className="w-full rounded-xl border border-emerald-500/40 bg-emerald-500/10 py-2.5 font-semibold text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
        >
          {busy ? "Verifying…" : "Activate Lifetime"}
        </button>

        <p className="mt-4 text-center text-xs text-slate-600">
          Lifetime owners earn +50 / +150 / +100 tokens forever — the Guardian pays for itself.
        </p>
      </div>
    </div>
  );
}
