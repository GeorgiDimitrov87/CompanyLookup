"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Building2, Download, ExternalLink, Globe, ShieldCheck } from "lucide-react";
import { getLookup } from "@/lib/api";
import type { Lookup } from "@/lib/types";
import { StatusBadge, ConfidenceBadge } from "@/components/StatusBadge";
import { ReportView } from "@/components/ReportView";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lookup, setLookup] = useState<Lookup | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getLookup(id)
      .then(setLookup)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !lookup) {
    return (
      <main className="flex flex-1 items-center justify-center min-h-screen bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
          <p className="text-sm text-zinc-500 font-medium">Generating Report Presentation…</p>
        </div>
      </main>
    );
  }

  const company = lookup.company;
  const stages = lookup.stages;

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-zinc-800/80 bg-zinc-900/60 backdrop-blur px-8 py-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push(`/lookups/${id}`)}
            className="flex items-center gap-2 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors bg-zinc-800/60 px-3 py-1.5 rounded-lg border border-zinc-700/50"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Pipeline
          </button>
          <span className="text-zinc-600">|</span>
          <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">
            Executive Report #{id?.slice(0, 8)}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700/60 text-xs font-medium text-zinc-200 transition-all"
          >
            <Download className="w-3.5 h-3.5" /> Export PDF / Print
          </button>
        </div>
      </header>

      {/* Main Presentation Body */}
      <div className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-10 space-y-8">
        {/* Company Hero Card */}
        <div className="glass rounded-3xl p-8 border border-zinc-800/80 bg-gradient-to-br from-indigo-950/40 via-zinc-900 to-violet-950/40 shadow-2xl relative overflow-hidden">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-start gap-5">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-300 font-extrabold text-3xl shadow-xl flex-shrink-0">
                {company?.name ? company.name.charAt(0) : "C"}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-3xl font-extrabold tracking-tight text-zinc-100">
                    {company?.name || lookup.company?.name || "Company"}
                  </h1>
                  <ShieldCheck className="w-6 h-6 text-emerald-400" />
                </div>

                {company?.domain && (
                  <a
                    href={`https://${company.domain}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 font-mono text-sm text-indigo-400 hover:underline"
                  >
                    <Globe className="w-4 h-4" /> https://{company.domain}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>

            <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-2 border-t md:border-t-0 pt-4 md:pt-0 border-zinc-800">
              <StatusBadge status={lookup.status === "COMPLETE" ? "Verified" : "Likely"} className="text-xs px-3 py-1" />
              <div className="text-right">
                <span className="text-[11px] text-zinc-500 font-medium block">Verification Score</span>
                <ConfidenceBadge confidence={stages.company_discovery?.confidence || "High"} score={stages.company_discovery?.confidence_score} />
              </div>
            </div>
          </div>
        </div>

        {/* Tabbed Executive Dashboard */}
        <ReportView stages={stages} company={company} />
      </div>
    </main>
  );
}
