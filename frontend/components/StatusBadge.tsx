import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  Verified: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Confirmed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Likely: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Probable: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Uncertain: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Unverified: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  "Not found": "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  "Not verified": "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

const CONFIDENCE_STYLES: Record<string, string> = {
  High: "text-emerald-400",
  Medium: "text-amber-400",
  Low: "text-red-400",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        STATUS_STYLES[status] || "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
        className,
      )}
    >
      {status}
    </span>
  );
}

export function ConfidenceBadge({ confidence, score }: { confidence: string; score?: number | null }) {
  return (
    <span className={cn("text-xs font-medium", CONFIDENCE_STYLES[confidence] || "text-zinc-400")}>
      {confidence}
      {score != null && <span className="text-zinc-500 ml-1">({Math.round(score)})</span>}
    </span>
  );
}
