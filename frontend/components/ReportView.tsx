"use client";

import { useState } from "react";
import {
  Globe, Mail, Phone, ExternalLink, Link2, ShieldCheck, Share2, Building2, User,
} from "lucide-react";
import type { StageResult, Evidence, Company } from "@/lib/types";
import { StatusBadge, ConfidenceBadge } from "@/components/StatusBadge";

export function ReportView({ stages, company }: { stages: Record<string, StageResult>; company?: Company | null }) {
  const [activeTab, setActiveTab] = useState<"overview" | "leadership" | "contacts" | "digital" | "evidence">("overview");

  const founderData = stages.founder_discovery?.data;
  const contactData = stages.contact_enrichment?.data;
  const websiteData = stages.website_verification?.data;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Executive Card Header */}
      <div className="glass rounded-2xl p-6 border border-zinc-800/80 bg-gradient-to-r from-zinc-900/90 via-zinc-900/50 to-zinc-900/90 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-2xl shadow-inner">
              {company?.name ? company.name.charAt(0) : "C"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-zinc-100">{company?.name || "Company Report"}</h2>
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-400 mt-1">
                {company?.domain && (
                  <a href={`https://${company.domain}`} target="_blank" rel="noreferrer" className="font-mono text-indigo-400 hover:underline flex items-center gap-1">
                    {company.domain} <ExternalLink className="w-3 h-3" />
                  </a>
                )}
                {company?.location && <span>· {company.location}</span>}
                {company?.industry && <span>· {company.industry}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right">
              <p className="text-xs text-zinc-500 font-medium">Overall Confidence</p>
              <ConfidenceBadge confidence={stages.company_discovery?.confidence || "Medium"} score={stages.company_discovery?.confidence_score} />
            </div>
          </div>
        </div>

        {/* Tab Selector Navigation */}
        <div className="flex border-b border-zinc-800/80 mt-6 pt-2 gap-2 overflow-x-auto">
          {[
            { id: "overview", label: "Overview" },
            { id: "leadership", label: "Leadership & Team" },
            { id: "contacts", label: "Direct Contacts" },
            { id: "digital", label: "Digital Footprint" },
            { id: "evidence", label: "Technical Evidence" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-indigo-500 text-indigo-300 bg-indigo-500/10"
                  : "border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 1: Executive Overview */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass p-4 rounded-xl border border-zinc-800">
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Website Status</p>
              <div className="mt-2 flex items-center justify-between">
                <StatusBadge status={stages.website_verification?.status || "Not found"} />
                <span className="text-xs text-zinc-400 font-mono">{websiteData?.url || "N/A"}</span>
              </div>
            </div>

            <div className="glass p-4 rounded-xl border border-zinc-800">
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Key Decision-Maker</p>
              <p className="mt-2 text-sm font-semibold text-zinc-100 truncate">
                {founderData?.primary?.name || "Not identified"}
              </p>
            </div>

            <div className="glass p-4 rounded-xl border border-zinc-800">
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Verified Contacts</p>
              <p className="mt-2 text-sm font-semibold text-zinc-100">
                {contactData?.emails?.length || 0} Emails · {contactData?.phones?.length || 0} Phones
              </p>
            </div>
          </div>

          {/* Website Signals */}
          {stages.website_verification && (
            <div className="glass p-5 rounded-xl border border-zinc-800 space-y-3">
              <h3 className="text-base font-semibold text-zinc-100">Website Verification Signals</h3>
              {websiteData?.signals && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(websiteData.signals).map(([k, v]) => (
                    <span key={k} className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                      v ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-zinc-800/60 text-zinc-500 border-zinc-700/40"
                    }`}>
                      {k.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Leadership & Team */}
      {activeTab === "leadership" && (
        <div className="space-y-4">
          {founderData?.primary ? (
            <div className="glass p-6 rounded-2xl border border-zinc-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-lg">
                    {founderData.primary.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-zinc-100">{founderData.primary.name}</h3>
                    <p className="text-xs text-indigo-400 font-semibold">{founderData.primary.position}</p>
                  </div>
                </div>

                {founderData.primary.linkedin_url && (
                  <a href={founderData.primary.linkedin_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 text-xs font-medium hover:bg-indigo-600/30 transition-colors">
                    LinkedIn Profile <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              {founderData.also_mentioned?.length > 0 && (
                <div className="pt-4 border-t border-zinc-800">
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Other Key Executives</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {founderData.also_mentioned.map((person: any, i: number) => (
                      <div key={i} className="p-3 rounded-xl bg-zinc-900/40 border border-zinc-800 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold text-zinc-200">{person.name}</p>
                          <p className="text-xs text-zinc-500">{person.position}</p>
                        </div>
                        {person.linkedin_url && (
                          <a href={person.linkedin_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300">
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="glass p-8 rounded-xl text-center text-zinc-500 text-sm">
              No founder or executive leadership profiles discovered.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Direct Contacts */}
      {activeTab === "contacts" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Emails */}
            <div className="glass p-5 rounded-xl border border-zinc-800 space-y-3">
              <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                <Mail className="w-4 h-4 text-indigo-400" /> Published Email Addresses
              </h3>
              {contactData?.emails?.length > 0 ? (
                <div className="space-y-2">
                  {contactData?.emails.map((e: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                      <span className="font-mono text-xs text-zinc-200">{e.email}</span>
                      <StatusBadge status={e.status} className="text-[10px]" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-zinc-500 italic">No emails found on company domain</p>
              )}
            </div>

            {/* Phones */}
            <div className="glass p-5 rounded-xl border border-zinc-800 space-y-3">
              <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                <Phone className="w-4 h-4 text-indigo-400" /> Phone Numbers
              </h3>
              {contactData?.phones?.length > 0 ? (
                <div className="space-y-2">
                  {contactData?.phones.map((p: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                      <span className="font-mono text-xs text-zinc-200">{p.phone}</span>
                      <StatusBadge status={p.status} className="text-[10px]" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-zinc-500 italic">No phone numbers published</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Digital Footprint */}
      {activeTab === "digital" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass p-4 rounded-xl border border-zinc-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-zinc-200">LinkedIn Profile</span>
              {stages.company_linkedin?.data?.linkedin_url ? (
                <a href={stages.company_linkedin.data.linkedin_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline flex items-center gap-1 font-medium">
                  View Profile <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-xs text-zinc-500">Not found</span>
              )}
            </div>

            <div className="glass p-4 rounded-xl border border-zinc-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-zinc-200">Facebook Page</span>
              {stages.facebook_presence?.data?.profile_url ? (
                <a href={stages.facebook_presence.data.profile_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline flex items-center gap-1 font-medium">
                  View Page <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-xs text-zinc-500">Not found</span>
              )}
            </div>

            <div className="glass p-4 rounded-xl border border-zinc-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-zinc-200">Instagram Profile</span>
              {stages.instagram_presence?.data?.profile_url ? (
                <a href={stages.instagram_presence.data.profile_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline flex items-center gap-1 font-medium">
                  View Page <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-xs text-zinc-500">Not found</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Technical Evidence */}
      {activeTab === "evidence" && (
        <div className="space-y-4">
          {Object.entries(stages).map(([stageKey, result]) => (
            <div key={stageKey} className="glass p-5 rounded-xl border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-sm text-zinc-200 capitalize">{stageKey.replace(/_/g, " ")}</h4>
                <StatusBadge status={result.status} />
              </div>

              {result.evidence?.length ? (
                <div className="space-y-1.5 pt-2">
                  {result.evidence.map((e, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-zinc-400 font-mono">
                      <Link2 className="w-3.5 h-3.5 mt-0.5 text-zinc-500 flex-shrink-0" />
                      <span>
                        <span className="text-indigo-400">[{e.source}]</span> {e.note}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-zinc-500 italic">No technical evidence records</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
