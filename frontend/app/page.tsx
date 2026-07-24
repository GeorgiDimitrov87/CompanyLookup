"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Clock, Building2, Sparkles } from "lucide-react";
import { listLookups, createLookup } from "@/lib/api";
import type { LookupListItem } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  COMPLETE: "text-emerald-400",
  PARTIAL: "text-amber-400",
  RUNNING: "text-blue-400",
  PENDING: "text-zinc-400",
  NEEDS_INPUT: "text-violet-400",
  FAILED: "text-red-400",
};

export default function Home() {
  const router = useRouter();
  const [companyName, setCompanyName] = useState("");
  const [location, setLocation] = useState("");
  const [industry, setIndustry] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recents, setRecents] = useState<LookupListItem[]>([]);

  useEffect(() => {
    listLookups().then(setRecents).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!companyName.trim()) return;
    setLoading(true);
    try {
      const res = await createLookup({
        company_name: companyName.trim(),
        location: location.trim() || undefined,
        industry: industry.trim() || undefined,
      });
      router.push(`/lookups/${res.job_id}`);
    } catch {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4 py-16 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-indigo-600/8 rounded-full blur-3xl" />

      <div className="relative z-10 w-full max-w-2xl space-y-10">
        {/* Hero */}
        <div className="text-center space-y-4 animate-fade-in-up">
          {/* <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-300 text-sm mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Intelligence
          </div> */}
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Company Intelligence
          </h1>
          <p className="text-zinc-400 text-lg max-w-md mx-auto">
            Discover companies, verify websites, find founders, and uncover digital presence — all from a single search.
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-4 animate-fade-in-up delay-100">
          <div className="flex items-center gap-3 bg-zinc-800/50 rounded-xl px-4 py-3 border border-zinc-700/50 focus-within:border-indigo-500/50 transition-colors">
            <Building2 className="w-5 h-5 text-zinc-400 flex-shrink-0" />
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Enter company name..."
              className="flex-1 bg-transparent outline-none text-lg text-zinc-100 placeholder:text-zinc-500"
              required
              autoFocus
            />
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-zinc-400 hover:text-zinc-300 transition-colors"
          >
            {showAdvanced ? "− Hide" : "+ Show"} optional filters
          </button>

          {showAdvanced && (
            <div className="grid grid-cols-2 gap-3 animate-fade-in-up">
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location (e.g. Columbus, OH)"
                className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-700/50 text-sm outline-none focus:border-indigo-500/50 transition-colors"
              />
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="Industry (e.g. manufacturing)"
                className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-700/50 text-sm outline-none focus:border-indigo-500/50 transition-colors"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !companyName.trim()}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-base flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <Search className="w-4.5 h-4.5" /> Analyze Company
              </>
            )}
          </button>
        </form>

        {/* Recent Lookups */}
        {recents.length > 0 && (
          <div className="space-y-3 animate-fade-in-up delay-200">
            <h2 className="text-sm font-medium text-zinc-500 uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-3.5 h-3.5" /> Recent Searches
            </h2>
            <div className="space-y-2">
              {recents.slice(0, 5).map((r) => (
                <button
                  key={r.job_id}
                  onClick={() => router.push(`/lookups/${r.job_id}`)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-zinc-900/50 border border-zinc-800/50 hover:border-zinc-700/50 transition-colors text-left group"
                >
                  <span className="text-zinc-200 group-hover:text-white transition-colors">
                    {r.company_name}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-medium ${STATUS_COLORS[r.status] || "text-zinc-400"}`}>
                      {r.status}
                    </span>
                    <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
