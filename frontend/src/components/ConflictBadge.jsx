import { AlertTriangle } from "lucide-react";

export default function ConflictBadge({ warning }) {
  if (!warning) return null;
  return (
    <div className="flex gap-2 bg-red-500/8 border border-red-500/25 rounded-xl px-3 py-2.5 w-full">
      <AlertTriangle size={13} className="text-red-400 shrink-0 mt-0.5" />
      <p className="text-[11px] text-red-300 leading-relaxed">{warning}</p>
    </div>
  );
}