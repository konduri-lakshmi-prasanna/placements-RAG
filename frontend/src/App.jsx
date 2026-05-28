import { useState, useEffect } from "react";
import {
  MessageSquare, LayoutGrid, SlidersHorizontal,
  BarChart2, FlaskConical, Cpu, Circle
} from "lucide-react";
import ChatPanel       from "./components/ChatPanel";
import EligibilityFilter from "./components/EligibilityFilter";
import HiringChart     from "./components/HiringChart";
import EvalPanel       from "./components/EvalPanel";
import { api }         from "./api";

const NAV = [
  { id:"chat",        label:"Ask PlacementIQ",   icon:MessageSquare },
  { id:"eligibility", label:"Eligibility Filter", icon:SlidersHorizontal },
  { id:"hiring",      label:"Hiring Charts",      icon:BarChart2 },
  { id:"eval",        label:"Evaluation Suite",   icon:FlaskConical },
];

export default function App() {
  const [tab,    setTab]    = useState("chat");
  const [stats,  setStats]  = useState(null);
  const [online, setOnline] = useState(null);  // null=checking, true, false

  useEffect(() => {
    api.health()
      .then(d => { setOnline(true); setStats(d); })
      .catch(() => setOnline(false));
    api.stats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex"
      style={{ fontFamily: "'Space Grotesk', sans-serif" }}>

      {/* ── Sidebar ───────────────────────────────────────────────── */}
      <aside className="w-60 shrink-0 flex flex-col border-r border-zinc-800/60 bg-zinc-950">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-zinc-800/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-violet-600/20 border border-violet-500/30
              flex items-center justify-center">
              <Cpu size={15} className="text-violet-400" />
            </div>
            <div>
              <p className="text-sm font-bold text-zinc-100 leading-none">PlacementIQ</p>
              <p className="text-[10px] text-zinc-600 mt-0.5 font-mono">SVECW · RAG-ATHON 24</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm
                transition-all duration-150 text-left
                ${tab === id
                  ? "bg-violet-600/15 text-violet-300 border border-violet-500/25"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 border border-transparent"
                }`}>
              <Icon size={15} className={tab === id ? "text-violet-400" : "text-zinc-600"} />
              {label}
            </button>
          ))}
        </nav>

        {/* Status footer */}
        <div className="px-4 py-4 border-t border-zinc-800/60">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest">
              System Status
            </span>
            <div className="flex items-center gap-1.5">
              <Circle
                size={6}
                className={online === null ? "text-zinc-600"
                  : online ? "text-emerald-400 fill-emerald-400"
                  : "text-red-500 fill-red-500"}
              />
              <span className={`text-[10px] font-mono
                ${online === null ? "text-zinc-600"
                : online ? "text-emerald-400"
                : "text-red-400"}`}>
                {online === null ? "checking" : online ? "online" : "offline"}
              </span>
            </div>
          </div>
          {stats && (
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-[10px] text-zinc-700">Chunks</span>
                <span className="text-[10px] font-mono text-zinc-500">{stats.chunk_count ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[10px] text-zinc-700">Model</span>
                <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[100px]">
                  claude-sonnet
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[10px] text-zinc-700">Vector DB</span>
                <span className="text-[10px] font-mono text-zinc-500">ChromaDB</span>
              </div>
            </div>
          )}
          {!online && online !== null && (
            <p className="text-[10px] text-red-400/70 mt-2 leading-tight">
              Backend offline. Start with <span className="font-mono">uvicorn main:app</span>
            </p>
          )}
        </div>
      </aside>

      {/* ── Main panel ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-h-0">
        {/* Top bar */}
        <header className="px-6 py-3.5 border-b border-zinc-800/60 flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-sm font-semibold text-zinc-100">
              {NAV.find(n => n.id === tab)?.label}
            </h1>
            <p className="text-[11px] text-zinc-600 mt-0.5">
              {tab === "chat"        && "Multi-hop RAG · Conflict detection · Out-of-corpus fallback"}
              {tab === "eligibility" && "Real-time filter across all 19 companies"}
              {tab === "hiring"      && "Section 3 — Multimodal chart data, now queryable"}
              {tab === "eval"        && "Official 30-query judge set · Section 9"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-1 bg-zinc-900 border border-zinc-800
              rounded-lg text-zinc-500">
              19 companies · 8 sections
            </span>
          </div>
        </header>

        {/* Panel content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {tab === "chat"        && <ChatPanel />}
          {tab === "eligibility" && <EligibilityFilter />}
          {tab === "hiring"      && <HiringChart />}
          {tab === "eval"        && <EvalPanel />}
        </div>
      </main>
    </div>
  );
}