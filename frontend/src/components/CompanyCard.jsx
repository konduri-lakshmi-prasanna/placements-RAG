import { Briefcase, GraduationCap, Zap, Clock } from "lucide-react";

const TECH_COLORS = {
  Python:        "bg-sky-500/10 text-sky-400 border-sky-500/25",
  Java:          "bg-orange-500/10 text-orange-400 border-orange-500/25",
  "C++":         "bg-indigo-500/10 text-indigo-400 border-indigo-500/25",
  Cloud:         "bg-cyan-500/10 text-cyan-400 border-cyan-500/25",
  "System Design":"bg-violet-500/10 text-violet-400 border-violet-500/25",
  DBMS:          "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
  Algorithms:    "bg-pink-500/10 text-pink-400 border-pink-500/25",
};

const PACKAGE_TIER = (pkg) => {
  if (pkg >= 40) return "text-emerald-400";
  if (pkg >= 25) return "text-sky-400";
  if (pkg >= 15) return "text-amber-400";
  return "text-zinc-400";
};

export default function CompanyCard({ company, onClick }) {
  const {
    name, min_cgpa, max_backlogs,
    package_lpa, bond_years, tech_focus
  } = company;

  const techColor = TECH_COLORS[tech_focus] || "bg-zinc-700/40 text-zinc-400 border-zinc-600/25";

  return (
    <button
      onClick={() => onClick(company)}
      className="text-left w-full bg-zinc-900/60 hover:bg-zinc-800/80 border border-zinc-800
        hover:border-violet-500/30 rounded-xl p-4 transition-all duration-200 group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-zinc-100 text-sm group-hover:text-white transition-colors">
          {name}
        </h3>
        <span className={`text-xs font-bold font-mono ${PACKAGE_TIER(package_lpa)}`}>
          ₹{package_lpa} LPA
        </span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="flex items-center gap-1.5">
          <GraduationCap size={12} className="text-zinc-500 shrink-0" />
          <span className="text-[11px] text-zinc-400">
            CGPA <span className="text-zinc-200 font-medium">{min_cgpa}</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Briefcase size={12} className="text-zinc-500 shrink-0" />
          <span className="text-[11px] text-zinc-400">
            <span className="text-zinc-200 font-medium">{max_backlogs}</span> bklg
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock size={12} className="text-zinc-500 shrink-0" />
          <span className="text-[11px] text-zinc-400">
            Bond <span className={`font-medium ${bond_years === 0 ? "text-emerald-400" : "text-zinc-200"}`}>
              {bond_years === 0 ? "None" : `${bond_years}yr`}
            </span>
          </span>
        </div>
      </div>

      {/* Tech focus badge */}
      <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md border font-mono ${techColor}`}>
        <Zap size={9} />
        {tech_focus}
      </span>
    </button>
  );
}