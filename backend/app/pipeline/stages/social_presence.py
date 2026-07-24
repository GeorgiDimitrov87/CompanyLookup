import logging
import re

from sqlalchemy.orm import Session

from app.pipeline.providers.searxng_client import searxng
from app.pipeline.scoring import WEIGHTS, compute_label, corroboration_bonus
from app.pipeline.utils import domain_to_name, get_job, get_stage_data, name_similarity, save_stage_result, update_job_status

logger = logging.getLogger(__name__)
W = WEIGHTS["social_presence"]

PLATFORM_SITES = {
    "facebook": "facebook.com",
    "instagram": "instagram.com",
}


def run(job_id: str, db: Session, platform: str = "facebook") -> str:
    stage_name = f"{platform}_presence"
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", stage_name)

    company = job.company
    if not company:
        save_stage_result(db, job_id, stage_name, "Not found", "Low", 0, data={}, evidence=[])
        return "NOT_FOUND"

    score = 0.0
    profile_url = None
    evidence = []

    # Source 1: outbound link from verified website
    website_data = get_stage_data(db, job_id, "website_verification")
    social_links = website_data.get("social_links", {}) if website_data else {}

    if platform in social_links:
        profile_url = social_links[platform]
        score += W["outbound_link"]
        evidence.append({"source": "website_outbound", "url": profile_url, "note": "First-party link"})

    # Source 2: SearXNG search with domain brand fallback
    site = PLATFORM_SITES.get(platform, f"{platform}.com")
    clean_brand = domain_to_name(company.domain) if company.domain else company.name
    queries = [f'site:{site} "{clean_brand}"', f'site:{site} {clean_brand}']

    all_results = []
    for q in queries:
        res = searxng.search(q, num_results=5)
        if res:
            all_results.extend(res)

    clean_dom = clean_brand.lower().replace(" ", "")
    for r in all_results:
        url = r.get("url", "")
        title = r.get("title", "")
        sim = name_similarity(clean_brand, title.split(" | ")[0].split(" - ")[0])
        if clean_dom and clean_dom in url.lower():
            sim = max(sim, 0.85)

        if sim > 0.35:
            if not profile_url:
                profile_url = url
            score += sim * W["searxng_match"]
            evidence.append({"source": "searxng", "url": url, "note": f"Match: {sim:.0%}"})
            break

    if profile_url and len(evidence) >= 2:
        score += corroboration_bonus([e["source"] for e in evidence])

    score = min(score, 100.0)

    if not profile_url:
        save_stage_result(db, job_id, stage_name, "Not found", "Low", 0,
                          data={"platform": platform},
                          evidence=[{"source": "searxng", "note": f"No {platform} page found"}])
        return "NOT_FOUND"

    status = "Confirmed" if score >= 70 else ("Probable" if score >= 40 else "Uncertain")
    save_stage_result(
        db, job_id, stage_name, status, compute_label(score), round(score, 1),
        data={"platform": platform, "profile_url": profile_url},
        evidence=evidence,
    )
    return "OK"
