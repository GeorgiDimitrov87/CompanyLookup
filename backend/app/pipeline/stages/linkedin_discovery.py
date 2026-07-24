import logging
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.pipeline.providers.searxng_client import searxng
from app.pipeline.scoring import WEIGHTS, compute_label, corroboration_bonus
from app.pipeline.utils import (
    domain_to_name, get_job, get_stage_data, name_similarity, save_stage_result, update_job_status,
)

logger = logging.getLogger(__name__)
W = WEIGHTS["company_linkedin"]


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "company_linkedin")

    company = job.company
    if not company:
        save_stage_result(db, job_id, "company_linkedin", "Not found", "Low", 0,
                          data={}, evidence=[{"source": "pipeline", "note": "No company resolved"}])
        return "NOT_FOUND"

    score = 0.0
    linkedin_url = None
    evidence = []
    best = None

    # Source 1: outbound link from verified website
    website_data = get_stage_data(db, job_id, "website_verification")
    social_links = website_data.get("social_links", {}) if website_data else {}
    is_js_shell = bool(website_data and website_data.get("signals", {}).get("is_js_shell"))

    if "linkedin" in social_links:
        raw = social_links["linkedin"]
        if "/company/" in raw.lower() or "/school/" in raw.lower():
            linkedin_url = raw
            score += W["outbound_link"]
            evidence.append({"source": "website_outbound", "url": raw, "note": "First-party link from verified site"})

    if is_js_shell:
        evidence.append({
            "source": "pipeline",
            "note": "Website is JS-rendered, limited outbound link extraction. Relying on search fallback.",
        })

    # Source 2: SearXNG search using valid site:domain syntax.
    # Also runs when the site is JS-rendered, since the outbound-link signal
    # above is unreliable in that case even if something happened to be found.
    if not linkedin_url or score < 60 or is_js_shell:
        clean_brand = domain_to_name(company.domain) if company.domain else company.name
        search_queries = [
            f'site:linkedin.com "{company.name}"',
            f'site:linkedin.com "{clean_brand}"',
            f'site:linkedin.com {company.name}',
        ]
        if company.domain:
            search_queries.append(f'site:linkedin.com "{company.domain}"')

        all_results = []
        for q in search_queries:
            res = searxng.search(q, num_results=5)
            if res:
                all_results.extend(res)

        best = _best_linkedin_match(all_results, company.name, company.domain, clean_brand, company.location)
        if best:
            if not linkedin_url:
                linkedin_url = best["url"]
            score += best["score_add"]
            evidence.extend(best["evidence"])

    score = min(score, 100.0)

    if not linkedin_url:
        note = "JS-rendered site limited outbound links" if is_js_shell else "No LinkedIn company page found"
        save_stage_result(db, job_id, "company_linkedin", "Not found", "Low", 0,
                          data={}, evidence=[{"source": "searxng", "note": note}])
        return "NOT_FOUND"

    status = "Confirmed" if score >= 70 else ("Probable" if score >= 40 else "Uncertain")
    save_stage_result(
        db, job_id, "company_linkedin", status, compute_label(score), round(score, 1),
        data={
            "linkedin_url": linkedin_url,
            "company_name": company.name,
            "matched_brand": best.get("matched_brand") if best else None,
        },
        evidence=evidence,
    )
    return "OK"


def _best_linkedin_match(results: list[dict], company_name: str, domain: str | None, clean_brand: str, location: str | None) -> dict | None:
    if not results:
        return None

    best = None
    best_score = 0.0

    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        if "/company/" not in url.lower() and "/school/" not in url.lower():
            continue

        clean_title = title.split(" | ")[0].split(" - ")[0].split(":")[0]
        sim1 = name_similarity(company_name, clean_title)
        sim2 = name_similarity(clean_brand, clean_title)
        sim = max(sim1, sim2)

        # Domain/brand token in URL check (e.g. linkedin.com/company/chaicodehq)
        clean_dom = clean_brand.lower().replace(" ", "")
        if clean_dom and clean_dom in url.lower():
            sim = max(sim, 0.85)

        if sim < 0.3:
            continue

        score_add = sim * W["searxng_name_match"]
        ev = [{"source": "searxng", "url": url, "note": f"LinkedIn match: {sim:.0%}"}]

        if domain and (domain.lower() in content.lower() or clean_dom in url.lower()):
            score_add += W["domain_corroboration"]
            ev.append({"source": "searxng", "note": "Domain/brand corroborated in result"})

        if location and location.lower() in content.lower():
            score_add += W["location_corroboration"]
            ev.append({"source": "searxng", "note": "Location corroborated"})

        if score_add > best_score:
            best_score = score_add
            best = {"url": url, "score_add": score_add, "evidence": ev, "matched_brand": clean_title}

    return best
