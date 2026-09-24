import { useState } from "react";

const STEPS = [
  { cmd: "npm install", desc: "Install JS deps + Tauri CLI" },
  { cmd: "pip install -r ai-core/requirements.txt", desc: "Install AI Core deps" },
  { cmd: "ollama pull llama3.1", desc: "Download the offline LLM" },
  { cmd: "npm run tauri build", desc: "Compile Rust + bundle the .msi installer" },
];

export default function InstallerBuilder() {
  const [done, setDone] = useState<number>(0);

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-title">⛭ INSTALLER BUILDER</div>
      <p className="text-[11px] text-slate-500 mb-3">
        Produces{" "}
        <code className="text-neon">
          src-tauri/target/release/bundle/msi/Xtobe Final Guardian_2.0.0_x64_en-US.msi
        </code>
      </p>
      <ol className="space-y-2 flex-1">
        {STEPS.map((s, i) => (
          <li
            key={s.cmd}
            className={`flex items-start gap-2 text-xs rounded-md border p-2 ${
              i < done ? "border-safe/40 bg-safe/5" : "border-edge bg-void"
            }`}
          >
            <button
              className="btn-neon shrink-0"
              onClick={() => setDone((d) => (i === d ? d + 1 : d))}
              disabled={i !== done}
            >
              {i < done ? "✓" : i + 1}
            </button>
            <div>
              <code className="text-neon">{s.cmd}</code>
              <div className="text-slate-500 text-[10px]">{s.desc}</div>
            </div>
          </li>
        ))}
      </ol>
      <div className="text-[10px] text-slate-500 mt-2">
        Run these in a terminal at the project root. The MSI bundles the Rust guardian service,
        the React UI, and registers the Python AI sidecar.
      </div>
    </div>
  );
}
