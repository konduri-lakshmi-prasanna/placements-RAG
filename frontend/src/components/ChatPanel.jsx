import { useState, useRef, useEffect } from "react";
import { Send, Loader2, AlertTriangle, GitFork, ExternalLink, ChevronDown } from "lucide-react";
import { api } from "../api";
import ConflictBadge from "./ConflictBadge";

const SUGGESTED = [
  "What is Amazon's CGPA requirement?",
  "Which companies allow 2 backlogs?",
  "A student with CGPA 7.6 and 1 backlog wants the highest-paying job",
  "Is the Amazon CGPA cutoff 6.4 or 7.0? Explain.",
  "Which company's package grew the most from 2021 to 2024?",
  "What is TCS's campus visit date at SVECW?",
];

const QUERY_TYPE_COLORS = {
  direct_lookup:       "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  threshold_filter:    "bg-sky-500/15 text-sky-300 border-sky-500/30",
  eligibility_package: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  tech_package:        "bg-violet-500/15 text-violet-300 border-violet-500/30",
  temporal:            "bg-amber-500/15 text-amber-300 border-amber-500/30",
  conflict:            "bg-red-500/15 text-red-300 border-red-500/30",
  out_of_corpus:       "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  general:             "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  computed:            "bg-orange-500/15 text-orange-300 border-orange-500/30",
  web_search:          "bg-blue-500/15 text-blue-300 border-blue-500/30",
  student_eligibility: "bg-teal-500/15 text-teal-300 border-teal-500/30",
};

function Message({ msg }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-xl bg-violet-600/30 border border-violet-500/30 flex items-center justify-center shrink-0 mt-1">
          <span className="text-violet-300 text-sm font-bold">IQ</span>
        </div>
      )}
      <div className={`max-w-[78%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-2`}>

        {/* Query type badge */}
        {!isUser && msg.query_type && (
          <span className={`text-xs px-3 py-1 rounded-full border font-mono w-fit font-semibold
            ${QUERY_TYPE_COLORS[msg.query_type] || QUERY_TYPE_COLORS.general}`}>
            {msg.query_type.replace(/_/g, " ")}
          </span>
        )}

        {/* Bubble */}
        <div className={`rounded-2xl px-5 py-4 text-base leading-relaxed
          ${isUser
            ? "bg-violet-600 text-white rounded-br-sm"
            : "bg-zinc-800/80 border border-zinc-700/50 text-zinc-100 rounded-bl-sm"
          }`}
        >
          {msg.text}
        </div>

        {/* Conflict warning */}
        {msg.conflict_warning && (
          <ConflictBadge warning={msg.conflict_warning} />
        )}

        {/* Multi-hop steps */}
        {msg.multihop_steps && msg.multihop_steps.length > 0 && (
          <div className="bg-zinc-900/60 border border-violet-500/20 rounded-xl px-4 py-3 w-full">
            <p className="text-xs text-violet-400 font-mono mb-2 uppercase tracking-widest font-semibold">
              Reasoning chain
            </p>
            {msg.multihop_steps.map((step, i) => (
              <div key={i} className="flex gap-2 items-start mb-1.5">
                <span className="text-violet-500 font-mono text-sm mt-0.5">{i + 1}.</span>
                <span className="text-zinc-300 text-sm">{step}</span>
              </div>
            ))}
          </div>
        )}

        {/* Sources toggle */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <button
            onClick={() => setShowSources(v => !v)}
            className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <ExternalLink size={13} />
            {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
            <ChevronDown size={13} className={`transition-transform ${showSources ? "rotate-180" : ""}`} />
          </button>
        )}
        {showSources && (
          <div className="flex flex-wrap gap-2">
            {msg.sources.map((s, i) => (
              <span key={i} className="text-xs bg-zinc-800 border border-zinc-700 rounded px-2.5 py-1 text-zinc-400 font-mono">
                {s.section}{s.company && s.company !== "ALL" ? ` · ${s.company}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-10 h-10 rounded-xl bg-zinc-700 flex items-center justify-center shrink-0 mt-1">
          <span className="text-zinc-300 text-sm font-bold">You</span>
        </div>
      )}
    </div>
  );
}

export default function ChatPanel() {
  const [messages, setMessages] = useState([{
    id: 0, role: "assistant",
    text: "Hello! I'm PlacementIQ — your SVECW placement intelligence assistant. Ask me about any of the 19 companies: eligibility criteria, packages, interview tips, or multi-hop reasoning.",
    query_type: null, sources: [], conflict_warning: null, multihop_steps: [],
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question) => {
    const q = (question || input).trim();
    if (!q || loading) return;

    const userMsg = { id: Date.now(), role: "user", text: q };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data = await api.query(q);
      setMessages(m => [...m, {
        id:               Date.now() + 1,
        role:             "assistant",
        text:             data.answer,
        query_type:       data.query_type,
        sources:          data.sources,
        conflict_warning: data.conflict_warning,
        multihop_steps:   data.multihop_steps,
      }]);
    } catch (e) {
      setMessages(m => [...m, {
        id: Date.now() + 1, role: "assistant",
        text: `⚠️ Error: ${e.message}`,
        query_type: "error", sources: [], conflict_warning: null, multihop_steps: [],
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin scrollbar-thumb-zinc-700">
        {messages.map(m => <Message key={m.id} msg={m} />)}
        {loading && (
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600/30 border border-violet-500/30 flex items-center justify-center">
              <span className="text-violet-300 text-sm font-bold">IQ</span>
            </div>
            <div className="bg-zinc-800/80 border border-zinc-700/50 rounded-2xl rounded-bl-sm px-5 py-4">
              <Loader2 size={18} className="text-violet-400 animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested queries (only when 1 message) */}
      {messages.length === 1 && (
        <div className="px-6 pb-4">
          <p className="text-xs text-zinc-500 mb-3 font-mono uppercase tracking-widest font-semibold">Try asking</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map(s => (
              <button key={s} onClick={() => send(s)}
                className="text-sm px-4 py-2 rounded-lg bg-zinc-800/60 border border-zinc-700/50
                  text-zinc-400 hover:text-zinc-200 hover:border-violet-500/40 transition-all">
                {s.length > 50 ? s.slice(0, 48) + "…" : s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-6 pb-6 pt-3 border-t border-zinc-800">
        <div className="flex gap-3 bg-zinc-800/60 border border-zinc-700 rounded-xl p-3">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Ask about eligibility, packages, interviews, trends…"
            className="flex-1 bg-transparent text-base text-zinc-100 placeholder-zinc-500
              outline-none px-2"
          />
          <button onClick={() => send()}
            disabled={!input.trim() || loading}
            className="w-10 h-10 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-30
              flex items-center justify-center transition-colors shrink-0">
            <Send size={17} className="text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}