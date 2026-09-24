import { useEffect, useState } from "react";
import { getTokenBalance, startAiGuardian } from "../api";
import type { TokenBalance } from "../types";

type ConsoleMessage = { role: "you" | "guardian"; text: string };

export default function RetroCRT() {
  const [awake, setAwake] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ConsoleMessage[]>([
    { role: "guardian", text: "Guardian initialized. Local inspection tools are available; security output remains factual." },
  ]);
  const [balance, setBalance] = useState<TokenBalance | null>(null);
  const refreshBalance = () => getTokenBalance().then(setBalance).catch(() => undefined);
  useEffect(() => { refreshBalance(); const id = setInterval(refreshBalance, 5000); return () => clearInterval(id); }, []);
  const send = () => {
    const text = input.trim();
    if (!text) return;
    setMessages((items) => [...items, { role: "you", text }, { role: "guardian", text: "Message queued locally. Use SCAN THREATS for a read-only inspection or ANCESTRAL LOG for local history." }]);
    setInput("");
  };
  const activate = async () => {
    if (awake) return;
    await startAiGuardian().catch(() => undefined);
    setAwake(true);
    setMessages((items) => [...items, { role: "guardian", text: "Vibranium core online. Guardian active. CLOAK DISENGAGED." }]);
  };
  return (
    <main className="retro-crt" aria-label="Xtobe retro CRT terminal">
      <div className="crt-scanlines" />
      <header className="crt-header"><span>PANASONIC</span><span>• CRT • 1987</span><span className="crt-no-signal">***NO SIGNAL***</span><span>{awake ? "SYSTEM AWAKENING" : "SYSTEM STANDBY"}</span></header>
      <section className="crt-content">
        <div className="crt-kicker">XTOBE-AI // GUARDIAN PROTOCOL</div>
        <h1 className="crt-title" data-text="XTOBE-AI">XTOBE-AI</h1>
        <h2 className="crt-subtitle">GUARDIAN OF THE THRONE</h2>
        <p className="crt-lore">THE FIRE DOES NOT CONSUME HIM. IT FORGES HIM.</p>
        <section className="crt-tactical"><span>VIBRANIUM CORE • v2.7.1</span><strong>1.3°S 30.5°E • CLOAK {awake ? "DISENGAGED" : "ENGAGED"}</strong><i>{awake ? "AWAKENING CORE // 100%" : "AWAITING AUTHORIZATION"}</i><b>TOKEN LEDGER: {balance ? balance.balance : "—"}</b></section>
        <button className="crt-activate" onClick={activate} disabled={awake}>{awake ? "GUARDIAN ACTIVE" : "ACTIVATE GUARDIAN"}</button>
        <section className="crt-console" aria-live="polite">{messages.map((message, index) => <div key={`${message.role}-${index}`} className={message.role === "you" ? "crt-you" : ""}>{message.role === "you" ? "YOU • SEEKER" : "XTOBE GUARDIAN"}: {message.text}</div>)}<div className="crt-actions"><button onClick={() => { setMessages((items) => [...items, { role: "guardian", text: "SCAN THREATS: use the standard Threat Matrix for a read-only process inspection." }]); }}>SCAN THREATS</button><button onClick={activate}>{awake ? "CLOAK ONLINE" : "CLOAK PC"}</button><button onClick={() => { setMessages((items) => [...items, { role: "guardian", text: "ANCESTRAL LOG: local Guardian history is available in the standard dashboard." }]); }}>ANCESTRAL LOG</button></div><div className="crt-input"><input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === "Enter" && send()} placeholder="Speak to the Guardian..." /><button onClick={send}>SEND</button></div><div className="crt-wave">{Array.from({ length: 24 }, (_, index) => <i key={index} />)}</div></section>
      </section>
      <footer className="crt-footer">LOCAL TERMINAL / NO CLOUD UPLINK / XTOBE FINAL GUARDIAN</footer>
    </main>
  );
}
