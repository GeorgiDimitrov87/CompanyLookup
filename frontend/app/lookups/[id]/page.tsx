"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Building2, FileText, ArrowRight } from "lucide-react";
import { getLookup, selectCandidate, connectWebSocket } from "@/lib/api";
import type { Lookup } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { StageTimeline } from "@/components/StageTimeline";
import { DisambiguationPicker } from "@/components/DisambiguationPicker";
import { StageCardsStream } from "@/components/StageCardsStream";

const JOB_STATUS_LABEL: Record<string, string> = {
  PENDING: "Analysis Starting…",
  RUNNING: "Analyzing Pipeline Stages",
  NEEDS_INPUT: "Requires Disambiguation",
  PARTIAL: "Analysis Complete",
  COMPLETE: "Analysis Complete",
  FAILED: "Lookup Unsuccessful",
};

export default function LookupPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lookup, setLookup] = useState<Lookup | null>(null);
  const [selecting, setSelecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getLookup(id);
      setLookup(data);
    } catch {}
  }, [id]);

  const isActive = lookup?.status === "RUNNING" || lookup?.status === "PENDING";
  const isFinished = lookup?.status === "COMPLETE" || lookup?.status === "PARTIAL";

  // Effect 1: Initial fetch on page load
  useEffect(() => {
    refresh();
  }, [id, refresh]);

  // Effect 2: Polling ONLY while RUNNING or PENDING — ZERO requests when COMPLETE
  useEffect(() => {
    if (!lookup) return;
    if (lookup.status === "RUNNING" || lookup.status === "PENDING") {
      const interval = setInterval(() => {
        refresh();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [lookup?.status, refresh]);

  // WebSocket for live updates while active
  useEffect(() => {
    if (!id || !isActive) return;
    const ws = connectWebSocket(id, () => refresh());
    wsRef.current = ws;
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [id, isActive, refresh]);

  async function handleSelectCandidate(candidateId: string) {
    if (!id) return;
    setSelecting(true);
    try {
      await selectCandidate(id, candidateId);
      await refresh();
    } finally {
      setSelecting(false);
    }
  }

  if (!lookup) {
    return (
      <main className="flex flex-1 items-center justify-center min-h-screen bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
          <p className="text-sm text-zinc-500 font-medium">Loading session…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header Bar */}
      <header className="border-b border-zinc-800/80 bg-zinc-900/40 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4 min-w-0">
          <button onClick={() => router.push("/")} className="text-zinc-400 hover:text-zinc-100 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold">
              <Building2 className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-bold text-zinc-100 truncate">
                {lookup.company?.name || (lookup.status === "NEEDS_INPUT" ? "Disambiguation Required" : "Company Analysis")}
              </h1>
              <p className="text-xs text-zinc-400 font-mono truncate">
                {lookup.company?.domain || JOB_STATUS_LABEL[lookup.status]}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <StatusBadge status={lookup.status === "COMPLETE" ? "Verified" : lookup.status === "PARTIAL" ? "Likely" : lookup.status} />

          {isFinished && (
            <button
              onClick={() => router.push(`/reports/${id}`)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/20 transition-all"
            >
              <FileText className="w-3.5 h-3.5" /> View Presentation Report <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left Sidebar: Pipeline Progress */}
        <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-zinc-800/80 p-6 bg-zinc-900/20 flex-shrink-0">
          <StageTimeline stages={lookup.stages} currentStage={lookup.current_stage} status={lookup.status} />
        </aside>

        {/* Right Content Area: Live Stage Cards Stream */}
        <div className="flex-1 p-6 lg:p-8 max-w-5xl overflow-y-auto">
          {lookup.status === "NEEDS_INPUT" && lookup.candidates ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <DisambiguationPicker
                candidates={lookup.candidates}
                onSelect={handleSelectCandidate}
                loading={selecting}
              />
            </div>
          ) : lookup.status === "FAILED" ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="glass rounded-2xl p-10 text-center space-y-4 border border-zinc-800">
                <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mx-auto text-xl font-bold">
                  !
                </div>
                <p className="text-xl font-bold text-zinc-200">Company Not Found</p>
                <p className="text-sm text-zinc-400 max-w-md mx-auto">
                  No verified domain or company entity could be matched automatically. Try adding location or industry details.
                </p>
                <button
                  onClick={() => router.push("/")}
                  className="px-6 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-sm font-medium transition-colors"
                >
                  Start New Search
                </button>
              </div>
            </div>
          ) : (
            <StageCardsStream stages={lookup.stages} company={lookup.company} />
          )}
        </div>
      </div>
    </main>
  );
}
