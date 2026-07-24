export interface Company {
  id: string;
  name: string;
  domain: string | null;
  location: string | null;
  industry: string | null;
}

export interface StageResult {
  stage: string;
  status: string;
  confidence: string;
  confidence_score: number | null;
  data: Record<string, any> | null;
  evidence: Evidence[] | null;
  created_at: string | null;
}

export interface Evidence {
  source: string;
  url?: string;
  note: string;
}

export interface Candidate {
  id: string;
  company_name: string;
  domain: string;
  score: number;
  reasoning: string;
  selected: boolean;
}

export interface Lookup {
  job_id: string;
  status: string;
  current_stage: string | null;
  company: Company | null;
  stages: Record<string, StageResult>;
  candidates: Candidate[] | null;
  created_at: string | null;
}

export interface LookupListItem {
  job_id: string;
  company_name: string;
  status: string;
  created_at: string | null;
}

export const STAGE_ORDER = [
  "company_discovery",
  "website_verification",
  "company_linkedin",
  "founder_discovery",
  "contact_enrichment",
  "facebook_presence",
  "instagram_presence",
  "meta_ads",
] as const;

export const STAGE_LABELS: Record<string, string> = {
  company_discovery: "Company Discovery",
  website_verification: "Website Verification",
  company_linkedin: "LinkedIn Presence",
  founder_discovery: "Founder Discovery",
  contact_enrichment: "Contact Enrichment",
  facebook_presence: "Facebook Presence",
  instagram_presence: "Instagram Presence",
  meta_ads: "Meta Advertising",
};
