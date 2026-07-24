"use client";

import { Check, X, Loader2 } from "lucide-react";
import type { StageResult } from "@/lib/types";
import { STAGE_ORDER, STAGE_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  stages: Record<string, StageResult>;
  currentStage: string | null;
  status: string;
}

export function StageTimeline({ stages, currentStage, status }: Props) {
  return (
    <div className="space-y-1">
      <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Pipeline Progress</h3>
      {STAGE_ORDER.map((stage, i) => {
        const result = stages[stage];
        const isRunning = currentStage === stage && status === "RUNNING";
        const isDone = !!result;
        const isFailed = result?.status === "Not found" || result?.status === "Uncertain";
        const isPending = !isDone && !isRunning;

        return (
          <div key={stage} className="flex items-start gap-3 relative">
            {/* Connector line */}
            {i < STAGE_ORDER.length - 1 && (
              <div className={cn(
                "absolute left-[11px] top-[24px] w-px h-[calc(100%+4px)]",
                isDone ? "bg-zinc-700" : "bg-zinc-800",
              )} />
            )}

            {/* Status dot */}
            <div className="relative z-10 mt-0.5 flex-shrink-0">
              {isRunning ? (
                <div className="w-[22px] h-[22px] rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                </div>
              ) : isDone && !isFailed ? (
                <div className="w-[22px] h-[22px] rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                </div>
              ) : isDone && isFailed ? (
                <div className="w-[22px] h-[22px] rounded-full bg-amber-500/20 flex items-center justify-center">
                  <X className="w-3.5 h-3.5 text-amber-400" />
                </div>
              ) : (
                <div className="w-[22px] h-[22px] rounded-full bg-zinc-800 border border-zinc-700" />
              )}
            </div>

            {/* Label */}
            <div className="pb-5 min-w-0">
              <p className={cn(
                "text-sm font-medium",
                isRunning ? "text-indigo-300" : isDone ? "text-zinc-200" : "text-zinc-500",
              )}>
                {STAGE_LABELS[stage]}
              </p>
              {result && (
                <p className="text-xs text-zinc-500 mt-0.5">{result.status} · {result.confidence}</p>
              )}
              {isRunning && (
                <p className="text-xs text-indigo-400/70 mt-0.5">Analyzing…</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
