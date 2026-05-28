import { useState, useMemo } from "react";
import { SlidersHorizontal, CheckCircle2, XCircle } from "lucide-react";

const COMPANIES = [
  { name:"TCS",          min_cgpa:7.5, max_backlogs:0, package_lpa:4.1,  bond_years:0, tech_focus:"System Design" },
  { name:"Infosys",      min_cgpa:8.0, max_backlogs:0, package_lpa:42.9, bond_years:0, tech_focus:"Java" },
  { name:"Deloitte",     min_cgpa:7.7, max_backlogs:1, package_lpa:9.6,  bond_years:1, tech_focus:"System Design" },
  { name:"Accenture",    min_cgpa:8.2, max_backlogs:0, package_lpa:17.3, bond_years:2, tech_focus:"System Design" },
  { name:"Amazon",       min_cgpa:6.4, max_backlogs:1, package_lpa:28.6, bond_years:2, tech_focus:"C++" },
  { name:"Flipkart",     min_cgpa:7.8, max_backlogs:2, package_lpa:25.3, bond_years:2, tech_focus:"Python" },
  { name:"Google",       min_cgpa:7.4, max_backlogs:0, package_lpa:42.0, bond_years:1, tech_focus:"Python" },
  { name:"Microsoft",    min_cgpa:6.1, max_backlogs:1, package_lpa:21.4, bond_years:0, tech_focus:"C++" },
  { name:"Wipro",        min_cgpa:6.7, max_backlogs:1, package_lpa:26.1, bond_years:1, tech_focus:"System Design" },
  { name:"Cognizant",    min_cgpa:8.4, max_backlogs:0, package_lpa:42.3, bond_years:2, tech_focus:"Java" },
  { name:"Capgemini",    min_cgpa:7.1, max_backlogs:0, package_lpa:38.3, bond_years:2, tech_focus:"C++" },
  { name:"IBM",          min_cgpa:7.5, max_backlogs:2, package_lpa:27.5, bond_years:0, tech_focus:"C++" },
  { name:"Adobe",        min_cgpa:7.5, max_backlogs:0, package_lpa:18.3, bond_years:1, tech_focus:"System Design" },
  { name:"Oracle",       min_cgpa:7.7, max_backlogs:0, package_lpa:17.3, bond_years:2, tech_focus:"Python" },
  { name:"SAP",          min_cgpa:8.4, max_backlogs:0, package_lpa:20.7, bond_years:2, tech_focus:"C++" },
  { name:"HCL",          min_cgpa:8.4, max_backlogs:1, package_lpa:28.1, bond_years:2, tech_focus:"Cloud" },
  { name:"Tech Mahindra",min_cgpa:8.1, max_backlogs:2, package_lpa:35.9, bond_years:1, tech_focus:"System Design" },
  { name:"Qualcomm",     min_cgpa:7.2, max_backlogs:2, package_lpa:41.3, bond_years:1, tech_focus:"Cloud" },
  { name:"Intel",        min_cgpa:7.0, max_backlogs:0, package_lpa:41.4, bond_years:0, tech_focus:"Python" },
  { name:"Samsung R&D",  min_cgpa:6.3, max_backlogs:2, package_lpa:7.6,  bond_years:2, tech_focus:"Java" },
];

const PKG_COLOR = (p) =>
  p >= 40 ? "text-emerald-400" : p >= 25 ? "text-sky-400" : p >= 15 ? "text-amber-400" : "text-zinc-400";

export default function EligibilityFilter() {
  const [cgpa,     setCgpa]     = useState(7.5);
  const [backlogs, setBacklogs] = useState(0);
  const [bondFree, setBondFree] = useState(false);
  const [sortBy,   setSortBy]   = useState("package");

  const eligible = useMemo(() => {
    return COMPANIES
      .filter(c =>
        cgpa >= c.min_cgpa &&
        backlogs <= c.max_backlogs &&
        (!bondFree || c.bond_years === 0)
      )
      .sort((a, b) =>
        sortBy === "package"
          ? b.package_lpa - a.package_lpa
          : a.min_cgpa - b.min_cgpa
      );
  }, [cgpa, backlogs, bondFree, sortBy]);

  const ineligible = COMPANIES.filter(c => !eligible.includes(c));

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-y-auto">
      {/* Controls */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-4">
          <SlidersHorizontal size={14} className="text-violet-400" />
          <span className="text-sm font-semibold text-zinc-200">Your Profile</span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* CGPA slider */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-[11px] text-zinc-500 font-mono uppercase tracking-widest">CGPA</label>
              <span className="text-sm font-bold text-violet-300 font-mono">{cgpa.toFixed(1)}</span>
            </div>
            <input type="range" min="5.0" max="10.0" step="0.1"
              value={cgpa} onChange={e => setCgpa(parseFloat(e.target.value))}
              className="w-full accent-violet-500 h-1.5 rounded-full cursor-pointer" />
            <div className="flex justify-between mt-0.5">
              <span className="text-[10px] text-zinc-700">5.0</span>
              <span className="text-[10px] text-zinc-700">10.0</span>
            </div>
          </div>

          {/* Backlogs */}
          <div>
            <label className="text-[11px] text-zinc-500 font-mono uppercase tracking-widest block mb-1.5">
              Backlogs
            </label>
            <div className="flex gap-2">
              {[0, 1, 2].map(b => (
                <button key={b} onClick={() => setBacklogs(b)}
                  className={`flex-1 py-1.5 rounded-lg text-sm font-mono border transition-all
                    ${backlogs === b
                      ? "bg-violet-600 border-violet-500 text-white"
                      : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-600"}`}>
                  {b}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between">
          {/* Bond-free toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <div onClick={() => setBondFree(v => !v)}
              className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer
                ${bondFree ? "bg-emerald-600" : "bg-zinc-700"}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform
                ${bondFree ? "translate-x-4" : "translate-x-0.5"}`} />
            </div>
            <span className="text-xs text-zinc-400">Bond-free only</span>
          </label>

          {/* Sort */}
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}
            className="text-[11px] bg-zinc-800 border border-zinc-700 text-zinc-400
              rounded-lg px-2 py-1 font-mono outline-none cursor-pointer">
            <option value="package">Sort: Package</option>
            <option value="cgpa">Sort: CGPA</option>
          </select>
        </div>
      </div>

      {/* Result summary */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 size={13} className="text-emerald-400" />
          <span className="text-xs text-zinc-400">
            <span className="text-emerald-400 font-bold">{eligible.length}</span> eligible
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle size={13} className="text-red-500/60" />
          <span className="text-xs text-zinc-500">
            {ineligible.length} not eligible
          </span>
        </div>
      </div>

      {/* Eligible companies */}
      {eligible.length === 0 ? (
        <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-6 text-center">
          <p className="text-sm text-zinc-500">No companies match your current criteria.</p>
          <p className="text-xs text-zinc-600 mt-1">Try lowering the CGPA slider.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {eligible.map((c, i) => (
            <div key={c.name}
              className="flex items-center justify-between bg-zinc-900/50 border border-zinc-800
                hover:border-emerald-500/30 rounded-xl px-4 py-3 transition-all group">
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-zinc-600 font-mono w-4">{i + 1}</span>
                <div>
                  <p className="text-sm font-medium text-zinc-200 group-hover:text-white">{c.name}</p>
                  <p className="text-[10px] text-zinc-600 font-mono mt-0.5">
                    min {c.min_cgpa} CGPA · {c.max_backlogs} bklg · {c.bond_years === 0 ? "no bond" : `${c.bond_years}yr bond`}
                  </p>
                </div>
              </div>
              <span className={`text-sm font-bold font-mono ${PKG_COLOR(c.package_lpa)}`}>
                ₹{c.package_lpa}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Ineligible (collapsed list) */}
      {ineligible.length > 0 && (
        <div className="mt-1">
          <p className="text-[10px] text-zinc-700 font-mono uppercase tracking-widest mb-2">Not eligible</p>
          <div className="flex flex-wrap gap-1.5">
            {ineligible.map(c => (
              <span key={c.name}
                className="text-[10px] px-2 py-1 bg-zinc-900/40 border border-zinc-800 rounded-lg
                  text-zinc-600 line-through decoration-zinc-700">
                {c.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}