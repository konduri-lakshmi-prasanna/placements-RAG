import { useState } from "react";
import { PlayCircle, Loader2, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { api } from "../api";

const DIFF_COLOR = {
  easy:   "text-emerald-400 bg-emerald-500/10 border-emerald-500/25",
  medium: "text-sky-400 bg-sky-500/10 border-sky-500/25",
  hard:   "text-amber-400 bg-amber-500/10 border-amber-500/25",
  expert: "text-red-400 bg-red-500/10 border-red-500/25",
};

const ScoreBar = ({ value, max = 1, color = "bg-violet-500" }) => (
  <div className="flex items-center gap-2">
    <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${Math.min((value / max) * 100, 100)}%` }} />
    </div>
    <span className="text-[11px] font-mono text-zinc-400 w-8 text-right">
      {typeof value === "number" ? (value <= 1 ? `${Math.round(value * 100)}%` : value.toFixed(2)) : value}
    </span>
  </div>
);

export default function EvalPanel() {
  const [running,  setRunning]  = useState(false);
  const [results,  setResults]  = useState(null);
  const [error,    setError]    = useState(null);
  const [expanded, setExpanded] = useState(null);

  const runEval = async () => {
    setRunning(true);
    setError(null);
    setResults(null);
    try {
      const data = await api.runEval();
      setResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-y-auto">
      {/* Header + Run button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-200">Evaluation Suite</h2>
          <p className="text-[11px] text-zinc-600 mt-0.5">30-query judge set from Section 9</p>
        </div>
        <button onClick={runEval} disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500
            disabled:opacity-40 text-white text-xs font-semibold transition-all">
          {running
            ? <><Loader2 size={13} className="animate-spin" />Running…</>
            : <><PlayCircle size={13} />Run Eval</>}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/8 border border-red-500/25 rounded-xl p-3 flex gap-2">
          <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {running && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 text-center space-y-2">
          <Loader2 size={24} className="text-violet-400 animate-spin mx-auto" />
          <p className="text-sm text-zinc-400">Running 30 queries against the RAG system…</p>
          <p className="text-xs text-zinc-600">This takes 60–120 seconds</p>
        </div>
      )}

      {results && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Answer Score", value: results.avg_answer_score,  color: "bg-violet-500" },
              { label: "Routing Acc.", value: results.routing_accuracy,   color: "bg-sky-500" },
              { label: "OOC Accuracy", value: results.ooc_accuracy,       color: "bg-emerald-500" },
            ].map(m => (
              <div key={m.label} className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3">
                <p className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest mb-2">{m.label}</p>
                <p className="text-xl font-bold font-mono text-zinc-100 mb-2">
                  {Math.round(m.value * 100)}<span className="text-sm text-zinc-500">%</span>
                </p>
                <ScoreBar value={m.value} color={m.color} />
              </div>
            ))}
          </div>

          {/* By difficulty */}
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-3">
            <p className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest mb-3">By Difficulty</p>
            <div className="space-y-2.5">
              {Object.entries(results.by_difficulty).map(([diff, score]) => (
                <div key={diff} className="flex items-center gap-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded-md border font-mono w-14 text-center
                    ${DIFF_COLOR[diff]}`}>{diff}</span>
                  <div className="flex-1">
                    <ScoreBar value={score}
                      color={diff === "easy" ? "bg-emerald-500" : diff === "medium" ? "bg-sky-500"
                        : diff === "hard" ? "bg-amber-500" : "bg-red-500"} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Individual results */}
          <div>
            <p className="text-[10px] text-zinc-600 font-mono uppercase tracking-widest mb-2">
              All {results.total_queries} Queries
            </p>
            <div className="space-y-1.5">
              {results.results.map(r => (
                <div key={r.id}>
                  <button onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                    className="w-full flex items-center gap-3 bg-zinc-900/40 hover:bg-zinc-800/60
                      border border-zinc-800 hover:border-zinc-700 rounded-xl px-3 py-2.5 transition-all text-left">
                    {/* ID */}
                    <span className="text-[10px] font-mono text-zinc-600 w-6">{r.id}</span>
                    {/* Status */}
                    {r.answer_score >= 0.5
                      ? <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                      : <XCircle size={13} className="text-red-500/60 shrink-0" />}
                    {/* Difficulty */}
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-mono
                      ${DIFF_COLOR[r.difficulty]}`}>{r.difficulty[0].toUpperCase()}</span>
                    {/* Question */}
                    <span className="flex-1 text-[11px] text-zinc-400 truncate">{r.question}</span>
                    {/* Score */}
                    <span className={`text-[11px] font-mono font-bold shrink-0
                      ${r.answer_score >= 0.7 ? "text-emerald-400"
                      : r.answer_score >= 0.4 ? "text-amber-400"
                      : "text-red-400"}`}>
                      {Math.round(r.answer_score * 100)}%
                    </span>
                    {/* Routing */}
                    <span className={`text-[9px] font-mono shrink-0
                      ${r.routing_ok ? "text-sky-400" : "text-zinc-600"}`}>
                      {r.routing_ok ? "✓route" : "✗route"}
                    </span>
                    {/* Time */}
                    <span className="text-[10px] text-zinc-700 font-mono shrink-0">{r.elapsed_s}s</span>
                  </button>

                  {/* Expanded answer preview */}
                  {expanded === r.id && (
                    <div className="mx-2 mb-1 bg-zinc-950/60 border border-zinc-800/60 rounded-b-xl
                      border-t-0 px-4 py-3 space-y-2">
                      <div>
                        <p className="text-[10px] text-zinc-600 font-mono mb-1">GOT TYPE</p>
                        <span className="text-[11px] font-mono text-violet-400">{r.got_type}</span>
                        <span className="text-[10px] text-zinc-700 ml-2">
                          (expected: {r.expected_type})
                        </span>
                      </div>
                      <div>
                        <p className="text-[10px] text-zinc-600 font-mono mb-1">ANSWER PREVIEW</p>
                        <p className="text-[11px] text-zinc-400 leading-relaxed">{r.answer_preview}</p>
                      </div>
                      {r.conflict_raised && (
                        <span className="text-[10px] px-2 py-0.5 bg-red-500/10 border border-red-500/25
                          text-red-400 rounded font-mono">conflict detected ✓</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!results && !running && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <PlayCircle size={32} className="text-zinc-700 mx-auto" />
            <p className="text-sm text-zinc-600">Click "Run Eval" to test all 30 judge queries</p>
            <p className="text-xs text-zinc-700">Tests routing accuracy, OOC detection, conflict handling</p>
          </div>
        </div>
      )}
    </div>
  );
}