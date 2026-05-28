import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell
} from "recharts";
import { BarChart2 } from "lucide-react";

const HIRING_DATA = [
  { company:"TCS",           sde:88,  analyst:42,  officer:70,  intern:44  },
  { company:"Infosys",       sde:30,  analyst:68,  officer:62,  intern:22  },
  { company:"Deloitte",      sde:42,  analyst:85,  officer:62,  intern:44  },
  { company:"Accenture",     sde:25,  analyst:22,  officer:52,  intern:68  },
  { company:"Amazon",        sde:42,  analyst:36,  officer:40,  intern:82  },
  { company:"Flipkart",      sde:58,  analyst:55,  officer:50,  intern:32  },
  { company:"Google",        sde:30,  analyst:92,  officer:46,  intern:30  },
  { company:"Microsoft",     sde:58,  analyst:58,  officer:36,  intern:68  },
  { company:"Wipro",         sde:42,  analyst:92,  officer:40,  intern:82  },
  { company:"Cognizant",     sde:48,  analyst:28,  officer:82,  intern:34  },
  { company:"Capgemini",     sde:68,  analyst:38,  officer:50,  intern:58  },
  { company:"IBM",           sde:58,  analyst:38,  officer:78,  intern:68  },
  { company:"Adobe",         sde:42,  analyst:80,  officer:62,  intern:48  },
  { company:"Oracle",        sde:35,  analyst:92,  officer:62,  intern:95  },
  { company:"SAP",           sde:48,  analyst:42,  officer:28,  intern:38  },
  { company:"HCL",           sde:48,  analyst:42,  officer:38,  intern:32  },
  { company:"Tech Mahindra", sde:58,  analyst:28,  officer:58,  intern:30  },
  { company:"Qualcomm",      sde:25,  analyst:38,  officer:82,  intern:78  },
  { company:"Intel",         sde:48,  analyst:48,  officer:42,  intern:48  },
  { company:"Samsung R&D",   sde:42,  analyst:80,  officer:42,  intern:38  },
];

const ROLES = [
  { key:"sde",     label:"SDE",     color:"#7c3aed" },
  { key:"analyst", label:"Analyst", color:"#0ea5e9" },
  { key:"officer", label:"Officer", color:"#10b981" },
  { key:"intern",  label:"Intern",  color:"#f59e0b" },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 shadow-xl">
      <p className="text-xs font-semibold text-zinc-200 mb-1.5">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-2 text-[11px]">
          <div className="w-2 h-2 rounded-full" style={{ background: p.fill }} />
          <span className="text-zinc-400">{p.name}:</span>
          <span className="text-zinc-200 font-mono font-medium">{p.value}</span>
        </div>
      ))}
      <p className="text-[10px] text-zinc-600 mt-1 border-t border-zinc-800 pt-1">
        Total: {payload.reduce((s, p) => s + p.value, 0)}
      </p>
    </div>
  );
};

export default function HiringChart() {
  const [activeRoles, setActiveRoles] = useState(
    Object.fromEntries(ROLES.map(r => [r.key, true]))
  );
  const [sortBy, setSortBy]   = useState("company");
  const [view,   setView]     = useState("grouped"); // grouped | stacked
  const [topN,   setTopN]     = useState(10);

  const toggleRole = (key) =>
    setActiveRoles(r => ({ ...r, [key]: !r[key] }));

  const sorted = [...HIRING_DATA]
    .sort((a, b) => {
      if (sortBy === "company") return a.company.localeCompare(b.company);
      return (b[sortBy] ?? 0) - (a[sortBy] ?? 0);
    })
    .slice(0, topN);

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-y-auto">
      <div className="flex items-center gap-2">
        <BarChart2 size={14} className="text-violet-400" />
        <span className="text-sm font-semibold text-zinc-200">Hiring Distribution by Role</span>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 bg-zinc-900/50 border border-zinc-800 rounded-xl p-3">
        {/* Role toggles */}
        <div className="flex gap-1.5 flex-wrap">
          {ROLES.map(r => (
            <button key={r.key} onClick={() => toggleRole(r.key)}
              className={`flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-lg border font-mono
                transition-all ${activeRoles[r.key]
                  ? "border-transparent text-zinc-900 font-semibold"
                  : "bg-zinc-800/60 border-zinc-700 text-zinc-500"}`}
              style={activeRoles[r.key] ? { background: r.color } : {}}>
              {r.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2 ml-auto items-center">
          {/* Sort */}
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}
            className="text-[11px] bg-zinc-800 border border-zinc-700 text-zinc-400
              rounded-lg px-2 py-1 font-mono outline-none">
            <option value="company">A–Z</option>
            {ROLES.map(r => <option key={r.key} value={r.key}>↓ {r.label}</option>)}
          </select>

          {/* View toggle */}
          <button onClick={() => setView(v => v === "grouped" ? "stacked" : "grouped")}
            className="text-[11px] px-2.5 py-1 rounded-lg border border-zinc-700 text-zinc-400
              hover:border-violet-500/40 font-mono transition-all">
            {view === "grouped" ? "Grouped" : "Stacked"}
          </button>

          {/* Top N */}
          <select value={topN} onChange={e => setTopN(Number(e.target.value))}
            className="text-[11px] bg-zinc-800 border border-zinc-700 text-zinc-400
              rounded-lg px-2 py-1 font-mono outline-none">
            <option value={10}>Top 10</option>
            <option value={20}>All 20</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} margin={{ top: 4, right: 8, left: -20, bottom: 60 }}
            barGap={view === "grouped" ? 2 : 0}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <XAxis dataKey="company" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }}
              angle={-40} textAnchor="end" interval={0} />
            <YAxis tick={{ fill: "#52525b", fontSize: 10 }} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(124,58,237,0.08)" }} />
            {ROLES.filter(r => activeRoles[r.key]).map(r => (
              <Bar key={r.key} dataKey={r.key} name={r.label} fill={r.color}
                stackId={view === "stacked" ? "s" : undefined}
                radius={view === "stacked" ? [0, 0, 0, 0] : [3, 3, 0, 0]}
                maxBarSize={32} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend summary */}
      <div className="grid grid-cols-4 gap-2">
        {ROLES.map(r => {
          const max  = Math.max(...HIRING_DATA.map(d => d[r.key]));
          const maxC = HIRING_DATA.find(d => d[r.key] === max);
          return (
            <div key={r.key} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ background: r.color }} />
                <span className="text-[10px] text-zinc-500 font-mono">{r.label}</span>
              </div>
              <p className="text-sm font-bold font-mono" style={{ color: r.color }}>{max}</p>
              <p className="text-[10px] text-zinc-600">{maxC?.company}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}