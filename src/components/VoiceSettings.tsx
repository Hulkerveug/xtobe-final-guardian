import { useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { previewLocalVoice } from "../api";

type VoiceStyle = "calm" | "warm" | "energetic" | "neutral";
const STYLES: { id: VoiceStyle; label: string; hint: string }[] = [
  { id: "calm", label: "Calm", hint: "clear and grounded" },
  { id: "warm", label: "Warm", hint: "friendly explanations" },
  { id: "energetic", label: "Energetic", hint: "brisk confirmations" },
  { id: "neutral", label: "Neutral", hint: "balanced delivery" },
];

export default function VoiceSettings() {
  const [enabled, setEnabled] = useState(() => localStorage.getItem("xtobe-voice-enabled") === "true");
  const [style, setStyle] = useState<VoiceStyle>(() => (localStorage.getItem("xtobe-voice-style") as VoiceStyle) || "calm");
  const [preview, setPreview] = useState("");
  const [audio, setAudio] = useState("");
  const [status, setStatus] = useState("");

  const save = (nextEnabled = enabled, nextStyle = style) => {
    localStorage.setItem("xtobe-voice-enabled", String(nextEnabled));
    localStorage.setItem("xtobe-voice-style", nextStyle);
  };
  const runPreview = async () => {
    setStatus("Preparing local preview…");
    try {
      const result = await previewLocalVoice(preview || "Xtobe local voice preview.", style);
      setAudio(convertFileSrc(result.path));
      setStatus(`Ready · ${(result.bytes / 1024).toFixed(0)} KB · local synthetic voice`);
    } catch (error) {
      setAudio("");
      setStatus(String(error));
    }
  };

  return (
    <section className="panel col-span-12">
      <div className="panel-title"><span className="text-neon">◈</span> VOICE & ACCESSIBILITY</div>
      <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_1fr_auto] gap-4 items-end">
        <label className="text-xs text-slate-300 flex items-center gap-2">
          <input type="checkbox" checked={enabled} onChange={(event) => { const next = event.target.checked; setEnabled(next); save(next, style); }} />
          Read responses aloud locally
          <span className="text-[10px] text-slate-500">(opt-in)</span>
        </label>
        <label className="text-xs text-slate-300">Voice style
          <select className="block mt-1 bg-edge border border-edge rounded p-2 w-full" value={style} onChange={(event) => { const next = event.target.value as VoiceStyle; setStyle(next); save(enabled, next); }}>
            {STYLES.map((item) => <option key={item.id} value={item.id}>{item.label} — {item.hint}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-300">Preview text
          <input className="block mt-1 bg-edge border border-edge rounded p-2 w-full" value={preview} maxLength={500} onChange={(event) => setPreview(event.target.value)} placeholder="Optional preview phrase" />
        </label>
        <div className="flex gap-2">
          <button className="btn-neon" onClick={runPreview}>PREVIEW</button>
          <button className="btn" onClick={() => { setEnabled(false); setStyle("calm"); save(false, "calm"); setAudio(""); setStatus("Reset to text-only defaults."); }}>RESET</button>
        </div>
      </div>
      {status && <p className="text-[10px] text-slate-500 mt-3">{status}</p>}
      {audio && <audio controls src={audio} className="mt-2 w-full max-w-md" />}
      <p className="text-[10px] text-slate-600 mt-2">Original generic local voices only. No celebrity likeness, cloud TTS, or model download. Text remains available at all times.</p>
    </section>
  );
}
