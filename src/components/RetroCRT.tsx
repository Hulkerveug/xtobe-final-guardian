import { useEffect, useRef, useState } from "react";
import { getTokenBalance, listProcesses, startAiGuardian } from "../api";
import type { ProcessInfo, TokenBalance } from "../types";

type View = "landing" | "cinematic" | "chat";
type Msg = { role: "guardian" | "user"; text: string };

function playTone(type: "activate" | "portal" | "scan", muted: boolean) {
  if (muted || typeof window === "undefined") return;
  const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) return;
  const context = new AudioContextClass();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const now = context.currentTime;
  oscillator.connect(gain).connect(context.destination);
  if (type === "activate") { oscillator.frequency.setValueAtTime(200, now); oscillator.frequency.exponentialRampToValueAtTime(900, now + .55); gain.gain.setValueAtTime(.12, now); gain.gain.exponentialRampToValueAtTime(.001, now + .65); oscillator.start(now); oscillator.stop(now + .65); }
  if (type === "portal") { oscillator.frequency.value = 58; gain.gain.setValueAtTime(.08, now); gain.gain.exponentialRampToValueAtTime(.001, now + 1.2); oscillator.start(now); oscillator.stop(now + 1.2); }
  if (type === "scan") { oscillator.frequency.value = 124; gain.gain.setValueAtTime(.04, now); gain.gain.exponentialRampToValueAtTime(.001, now + 1.3); oscillator.start(now); oscillator.stop(now + 1.3); }
  oscillator.addEventListener("ended", () => void context.close());
}

function Particles() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    const points = Array.from({ length: 72 }, () => ({ x: Math.random(), y: Math.random(), vx: (Math.random() - .5) * .001, vy: (Math.random() - .5) * .001 }));
    const resize = () => { canvas.width = innerWidth * devicePixelRatio; canvas.height = innerHeight * devicePixelRatio; };
    resize(); addEventListener("resize", resize);
    const draw = () => { ctx.clearRect(0, 0, canvas.width, canvas.height); points.forEach((p, i) => { p.x += p.vx; p.y += p.vy; if (p.x < 0 || p.x > 1) p.vx *= -1; if (p.y < 0 || p.y > 1) p.vy *= -1; ctx.beginPath(); ctx.fillStyle = "rgba(255,138,26,.7)"; ctx.shadowColor = "#ff8a1a"; ctx.shadowBlur = 8 * devicePixelRatio; ctx.arc(p.x * canvas.width, p.y * canvas.height, 1.2 * devicePixelRatio, 0, Math.PI * 2); ctx.fill(); points.slice(i + 1).forEach((q) => { const d = Math.hypot(p.x - q.x, p.y - q.y); if (d < .12) { ctx.beginPath(); ctx.strokeStyle = "rgba(255,138,26,.12)"; ctx.moveTo(p.x * canvas.width, p.y * canvas.height); ctx.lineTo(q.x * canvas.width, q.y * canvas.height); ctx.stroke(); } }); }); raf = requestAnimationFrame(draw); };
    draw(); return () => { cancelAnimationFrame(raf); removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={ref} className="crt-particles" aria-hidden="true" />;
}

export default function RetroCRT() {
  const [view, setView] = useState<View>("cinematic");
  const [slide, setSlide] = useState(0);
  const [awake, setAwake] = useState(false);
  const [input, setInput] = useState("");
  const [balance, setBalance] = useState<TokenBalance | null>(null);
  const [messages, setMessages] = useState<Msg[]>([{ role: "guardian", text: "Guardian initialized. Local inspection tools are available; security output remains factual." }]);
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [scanning, setScanning] = useState(false);
  const [muted, setMuted] = useState(false);
  useEffect(() => { getTokenBalance().then(setBalance).catch(() => undefined); }, []);
  useEffect(() => { if (view !== "cinematic") return; const id = setInterval(() => setSlide((value) => (value + 1) % 4), 2600); const complete = setTimeout(() => setView("chat"), 10800); return () => { clearInterval(id); clearTimeout(complete); }; }, [view, muted]);
  const activate = async () => { playTone("activate", muted); await startAiGuardian().catch(() => undefined); setAwake(true); setView("chat"); setMessages((items) => [...items, { role: "guardian", text: "Vibranium core online. Guardian active. CLOAK DISENGAGED." }]); };
  const runScan = async () => {
    playTone("scan", muted);
    setScanning(true);
    const result = await listProcesses().catch(() => [] as ProcessInfo[]);
    setProcesses(result);
    const flagged = result.filter((item) => item.risk !== "safe").length;
    setMessages((items) => [...items, { role: "guardian", text: `Local process scan complete. ${result.length} processes inspected; ${flagged} flagged for review.` }]);
    setScanning(false);
  };
  const send = () => { const text = input.trim(); if (!text) return; setMessages((items) => [...items, { role: "user", text }, { role: "guardian", text: "Message queued locally. Use SCAN THREATS for read-only inspection or ANCESTRAL LOG for local history." }]); setInput(""); };
  const note = (text: string) => setMessages((items) => [...items, { role: "guardian", text }]);
  const replay = () => { playTone("portal", muted); setSlide(0); setView("cinematic"); };
  return <main className="retro-crt" aria-label="Xtobe AI Guardian console"><Particles /><div className="crt-scanlines" /><header className="crt-header"><span>XTOBE-AI // FINAL GUARDIAN 2.0.0</span><span>● TAURI CONNECTED</span><button onClick={() => setMuted((value) => !value)}>{muted ? "SOUND OFF" : "SOUND ON"}</button><button onClick={replay}>REPLAY INTRO</button></header>{view === "landing" && <section className="crt-content"><p className="crt-kicker">GUARDIAN OF PC • PURE DARK ENERGY</p><h1 className="crt-title" data-text="XTOBE-AI">XTOBE-AI</h1><p className="crt-lore">THE FIRE DOES NOT CONSUME HIM. IT FORGES HIM.</p><section className="crt-tactical"><span>VIBRANIUM CORE • v2.7.1</span><strong>1.3°S 30.5°E • CLOAK {awake ? "DISENGAGED" : "ENGAGED"}</strong><i>{awake ? "CORE ONLINE" : "AWAITING AUTHORIZATION"}</i><b>TOKEN LEDGER: {balance ? balance.balance : "—"}</b></section><button className="crt-activate" onClick={activate}>ACTIVATE GUARDIAN</button></section>}{view === "cinematic" && <section className="crt-cinematic"><div className="crt-progress">{[0, 1, 2, 3].map((item) => <i className={item === slide ? "active" : ""} key={item} />)}</div><h2>{["ENTERING NO SIGNAL WAKANDA", "XTOBE-AI AWAKENING", "GUARDIAN OF THE THRONE", "ENTERING WAKANDA"][slide]}</h2><p>{["WHITE NOISE FLASH • SECURE LINK", "VIBRANIUM MASK • PROTOCOL 7", "NOT DEAD • VISUAL THEME ONLY", "LIGHTSPEED WARPED REALM"][slide]}</p><button onClick={() => setView("chat")}>SKIP INTRO →</button></section>}{view === "chat" && <section className="crt-chat"><div className="crt-messages">{messages.map((message, index) => <p className={message.role} key={`${message.role}-${index}`}><b>{message.role === "guardian" ? "XTOBE GUARDIAN" : "YOU • SEEKER"}</b>{message.text}</p>)}</div><div className="crt-dashboard"><div><span>THREAT STATUS</span><b className="crt-cyan">{processes.length ? `${processes.filter((item) => item.risk !== "safe").length} FLAGGED` : "READY"}</b></div><div><span>VIBRANIUM SHIELD</span><b className="crt-amber">{awake ? "ACTIVE" : "STANDBY"}</b></div><button onClick={runScan} disabled={scanning}>{scanning ? "SCANNING..." : "RUN DEEP SCAN"}</button></div><div className="crt-actions"><button onClick={() => note("SCAN THREATS: use the standard Threat Matrix for a read-only process inspection.")}>SCAN THREATS</button><button onClick={activate}>{awake ? "CLOAK ONLINE" : "CLOAK PC"}</button><button onClick={() => note("ANCESTRAL LOG: local Guardian history is available in the standard dashboard.")}>ANCESTRAL LOG</button></div><div className="crt-input"><input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === "Enter" && send()} placeholder="Speak to the Guardian..." /><button onClick={send}>SEND</button></div><div className="crt-wave">{Array.from({ length: 32 }, (_, index) => <i key={index} />)}</div></section>}<footer className="crt-footer">LOCAL TERMINAL / NO CLOUD UPLINK / FACTUAL SECURITY OUTPUT</footer></main>;
}
