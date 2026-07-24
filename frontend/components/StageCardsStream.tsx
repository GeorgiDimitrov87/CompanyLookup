"use client";

import { Globe, Mail, Phone, ExternalLink, Link2, ShieldCheck } from "lucide-react";
import type { StageResult, Company } from "@/lib/types";
import { STAGE_ORDER, STAGE_LABELS } from "@/lib/types";
import { StatusBadge, ConfidenceBadge } from "@/components/StatusBadge";

interface Props {
  stages: Record<string, StageResult>;
  company?: Company | null;
}

const STAGE_TITLES: Record<string, string> = {
  company_discovery: "Company Discovery",
  website_verification: "Website Verification",
  company_linkedin: "LinkedIn Presence",
  founder_discovery: "Founder / Decision-Maker",
  contact_enrichment: "Contact Information",
  facebook_presence: "Facebook Presence",
  instagram_presence: "Instagram Presence",
  meta_ads: "Meta Advertising",
};

export function StageCardsStream({ stages, company }: Props) {
  return (
    <div className="space-y-6">
      {/* Top Company Header Card */}
      {company && (
        <div className="glass rounded-2xl p-6 border border-zinc-800/80 bg-gradient-to-r from-zinc-900/90 via-zinc-900/50 to-zinc-900/90 shadow-xl flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-xl">
              {company.name ? company.name.charAt(0) : "C"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-zinc-100">{company.name}</h2>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              {company.domain && (
                <a
                  href={`https://${company.domain}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-mono text-indigo-400 hover:underline flex items-center gap-1 mt-0.5"
                >
                  {company.domain} <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stream of Stage Cards */}
      {STAGE_ORDER.map((stageKey) => {
        const result = stages[stageKey];
        if (!result) return null;

        const data = result.data || {};
        const evidence = result.evidence || [];

        return (
          <div
            key={stageKey}
            className="glass rounded-2xl p-6 border border-zinc-800/80 bg-zinc-900/40 shadow-xl space-y-4 animate-fade-in-up"
          >
            {/* Card Header: Title & Badges */}
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800/60">
              <h3 className="text-base font-bold text-zinc-100">{STAGE_TITLES[stageKey] || STAGE_LABELS[stageKey]}</h3>
              <div className="flex items-center gap-2">
                <ConfidenceBadge confidence={result.confidence} score={result.confidence_score} />
                <StatusBadge status={result.status} />
              </div>
            </div>

            {/* Stage-Specific Details */}
            {stageKey === "website_verification" && (
              <div className="space-y-3">
                {data.url && (
                  <div className="text-xs font-mono text-zinc-400 flex items-center gap-1.5">
                    <span className="text-zinc-500 font-sans font-semibold">URL:</span>
                    <a href={data.url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline flex items-center gap-1">
                      {data.url} <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}

                {data.signals && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {Object.entries(data.signals).map(([k, v]) => (
                      <span
                        key={k}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${
                          v
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-zinc-800/60 text-zinc-500 border-zinc-700/40"
                        }`}
                      >
                        {k.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {stageKey === "company_linkedin" && (
              <div className="space-y-2">
                {data.linkedin_url ? (
                  <a
                    href={data.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-mono text-indigo-400 hover:underline flex items-center gap-1.5"
                  >
                    <Globe className="w-3.5 h-3.5" /> {data.linkedin_url} <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <p className="text-xs text-zinc-500 italic">No LinkedIn profile found</p>
                )}
              </div>
            )}

            {stageKey === "founder_discovery" && (
              <div className="space-y-4">
                {data.primary ? (
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                    <div className="w-10 h-10 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-sm">
                      {data.primary.name ? data.primary.name.charAt(0) : "F"}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-zinc-100">{data.primary.name}</p>
                      <p className="text-xs text-zinc-400">{data.primary.position || "Founder / Executive"}</p>
                    </div>
                    {data.primary.linkedin_url && (
                      <a href={data.primary.linkedin_url} target="_blank" rel="noreferrer" className="ml-auto text-indigo-400 hover:text-indigo-300">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 italic">No primary founder identified</p>
                )}

                {data.also_mentioned && data.also_mentioned.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Also Mentioned</p>
                    <div className="space-y-1">
                      {data.also_mentioned.map((person: any, idx: number) => (
                        <div key={idx} className="text-xs text-zinc-300 flex items-center justify-between">
                          <span>
                            <strong>{person.name}</strong> — {person.position}
                          </span>
                          {person.linkedin_url && (
                            <a href={person.linkedin_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline text-[11px]">
                              LinkedIn
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {stageKey === "contact_enrichment" && (
              <div className="space-y-3">
                {/* Emails */}
                {data.emails && data.emails.length > 0 ? (
                  <div className="space-y-1.5">
                    {data.emails.map((e: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs">
                        <div className="flex items-center gap-2 font-mono text-zinc-200">
                          <Mail className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{typeof e === "string" ? e : e.email}</span>
                          {e.source && <span className="text-[10px] text-zinc-500">({e.source})</span>}
                        </div>
                        {e.status && <StatusBadge status={e.status} className="text-[10px]" />}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 italic">No published emails found</p>
                )}

                {/* Phones */}
                {data.phones && data.phones.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    {data.phones.map((p: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs">
                        <div className="flex items-center gap-2 font-mono text-zinc-200">
                          <Phone className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{typeof p === "string" ? p : p.phone}</span>
                        </div>
                        {p.status && <StatusBadge status={p.status} className="text-[10px]" />}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {(stageKey === "facebook_presence" || stageKey === "instagram_presence") && (
              <div className="space-y-2">
                {data.profile_url ? (
                  <a
                    href={data.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-mono text-indigo-400 hover:underline flex items-center gap-1.5"
                  >
                    <Globe className="w-3.5 h-3.5" /> {data.profile_url} <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <p className="text-xs text-zinc-500 italic">No profile found</p>
                )}
              </div>
            )}

            {stageKey === "meta_ads" && (
              <div className="space-y-2 text-xs text-zinc-400">
                {data.reason ? (
                  <p className="italic text-zinc-500">{data.reason}</p>
                ) : (
                  <p>Active Ad Campaigns: {data.active_ads_count ?? 0}</p>
                )}
              </div>
            )}

            {/* Technical Evidence Section */}
            {evidence.length > 0 && (
              <div className="pt-3 border-t border-zinc-800/60 space-y-1">
                <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-1">Evidence</p>
                {evidence.map((item: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-zinc-400 font-mono">
                    <Link2 className="w-3.5 h-3.5 mt-0.5 text-zinc-500 flex-shrink-0" />
                    <span>
                      <span className="text-indigo-400">[{item.source}]</span> {item.note}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
