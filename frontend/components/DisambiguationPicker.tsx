"use client";

import { useState } from "react";
import { Globe, ArrowRight } from "lucide-react";
import type { Candidate } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  candidates: Candidate[];
  onSelect: (candidateId: string) => void;
  loading: boolean;
}

export function DisambiguationPicker({ candidates, onSelect, loading }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="glass rounded-2xl p-6 space-y-4 animate-fade-in-up">
      <div>
        <h3 className="text-lg font-semibold text-zinc-100">Multiple matches found</h3>
        <p className="text-sm text-zinc-400 mt-1">Select the correct company to continue analysis.</p>
      </div>

      <div className="space-y-2">
        {candidates.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelected(c.id)}
            className={cn(
              "w-full text-left p-4 rounded-xl border transition-all",
              selected === c.id
                ? "border-indigo-500/50 bg-indigo-500/10"
                : "border-zinc-700/50 bg-zinc-800/30 hover:border-zinc-600/50",
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium text-zinc-100">{c.company_name}</p>
                <div className="flex items-center gap-2 mt-1 text-sm text-zinc-400">
                  <Globe className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate">{c.domain}</span>
                </div>
                {c.reasoning && (
                  <p className="text-xs text-zinc-500 mt-2">{c.reasoning}</p>
                )}
              </div>
              <span className="text-xs font-medium text-indigo-400 flex-shrink-0">
                {Math.round(c.score)}%
              </span>
            </div>
          </button>
        ))}
      </div>

      <button
        onClick={() => selected && onSelect(selected)}
        disabled={!selected || loading}
        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-medium flex items-center justify-center gap-2 disabled:opacity-40 transition-all"
      >
        {loading ? (
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <>Continue with selection <ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </div>
  );
}
