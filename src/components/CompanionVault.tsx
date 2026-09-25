import { useEffect, useState } from "react";
type Story = { id: string; timestamp: number; mood: string; topic: string; note: string; isShared: boolean };

type Basics = { name: string; interests: string; mood: string };

export default function CompanionVault({ onBack, onEnterCRT, tokenBalance }: { onBack: () => void; onEnterCRT: () => void; tokenBalance: number }) {
  const [stories, setStories] = useState<Story[]>([]);
  const [basics, setBasics] = useState<Basics>({ name: "", interests: "", mood: "neutral" });
  const [note, setNote] = useState("");
  const [topic, setTopic] = useState("human nature");
  const [mood, setMood] = useState("reflective");
  useEffect(() => {
    try { setStories(JSON.parse(localStorage.getItem("xtobe-companion-stories") ?? "[]")); } catch { setStories([]); }
    try { setBasics(JSON.parse(localStorage.getItem("xtobe-user-basics") ?? "null") ?? { name: "", interests: "", mood: "neutral" }); } catch { /* ignore malformed local data */ }
  }, []);
  const saveStories = (next: Story[]) => { const bounded = next.slice(0, 100); setStories(bounded); localStorage.setItem("xtobe-companion-stories", JSON.stringify(bounded)); };
  const addStory = () => {
    if (!note.trim()) return;
    const story: Story = { id: crypto.randomUUID(), timestamp: Date.now(), mood, topic, note: note.trim(), isShared: false };
    saveStories([story, ...stories]);
    const match = note.match(/i (?:like|love|enjoy) ([^.,!?]+)/i);
    if (match) { const next = { ...basics, interests: basics.interests ? `${basics.interests}, ${match[1].trim()}` : match[1].trim() }; setBasics(next); localStorage.setItem("xtobe-user-basics", JSON.stringify(next)); }
    setNote("");
  };
  const toggleShare = (id: string) => saveStories(stories.map((story) => story.id === id ? { ...story, isShared: !story.isShared } : story));
  return <main className="panel max-w-4xl mx-auto p-5 flex flex-col gap-4"><div className="flex items-center justify-between"><h2 className="text-sm text-warn">COMPANION VAULT • USER-RELATED ONLY</h2><div className="flex gap-2"><button className="btn-ghost" onClick={onEnterCRT}>ENTER CRT VIEW</button><button className="btn-ghost" onClick={onBack}>BACK TO GUARDIAN</button></div></div><p className="text-xs text-slate-400">Stories are saved locally only. Sharing is opt-in. The assistant does not invent personal history or claim analysis that has not been performed.</p><div className="grid grid-cols-3 gap-2 text-xs"><div className="panel p-3"><span className="text-slate-500">USER BASICS</span><b className="block mt-1">{basics.name || "Not set"}</b><small>{basics.interests || "No interests recorded"}</small></div><div className="panel p-3"><span className="text-slate-500">STORIES</span><b className="block mt-1">{stories.length} / 100</b><small>{stories.filter((story) => story.isShared).length} opted in</small></div><div className="panel p-3"><span className="text-slate-500">DEEP LEARNING</span><b className="block mt-1">{tokenBalance} tokens</b><small>Opt-in only</small></div></div><section className="panel p-4 flex flex-col gap-3"><label className="text-xs text-slate-400" htmlFor="companion-note">ADD A USER-AUTHORED NOTE</label><div className="grid grid-cols-2 gap-2"><input className="btn-ghost" value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Topic" /><select className="btn-ghost" value={mood} onChange={(event) => setMood(event.target.value)}><option>reflective</option><option>joyful</option><option>contemplative</option><option>resilient</option><option>curious</option></select></div><textarea id="companion-note" className="btn-ghost min-h-24" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Share your own reflection. Nothing is sent to a cloud service." /><button className="btn-neon self-end" disabled={!note.trim()} onClick={addStory}>SAVE LOCALLY</button></section><section className="flex flex-col gap-2">{stories.length === 0 && <p className="text-xs text-slate-500">No local stories yet.</p>}{stories.map((story) => <article className="panel p-3" key={story.id}><div className="flex justify-between text-[10px] text-slate-500"><span>{story.topic} · {story.mood} · {new Date(story.timestamp).toLocaleString()}</span><button className="btn-ghost" onClick={() => toggleShare(story.id)}>{story.isShared ? "SHARED • ACCURATE" : "NOT SHARED • OPT-IN"}</button></div><p className="text-sm whitespace-pre-wrap mt-2">{story.note}</p></article>)}</section><p className="text-[10px] text-slate-500">Token in-depth learning is not automatic. Any future analysis must be separately enabled by the user and run locally.</p></main>;
}
