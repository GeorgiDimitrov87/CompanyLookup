import logging
import re

from sqlalchemy.orm import Session

from app.pipeline.providers.fetch_service import (
    PageData, fetch_page, find_about_page, find_contact_page, normalize_url,
)
from app.pipeline.scoring import WEIGHTS, compute_label, status_from_score
from app.pipeline.utils import (
    domain_to_name, get_job, name_similarity, normalize_company_name,
    save_stage_result, update_job_status,
)

logger = logging.getLogger(__name__)
W = WEIGHTS["website_verification"]

INDIAN_PERSONAL_MOBILE_RE = re.compile(r"^\+?91[\s\-]?[789]\d{9}$")


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "website_verification")

    company = job.company
    if not company or not company.domain:
        save_stage_result(db, job_id, "website_verification", "Not found", "Low", 0,
                          data={"reason": "No domain resolved"}, evidence=[])
        return "NOT_FOUND"

    url = normalize_url(company.domain)
    homepage = fetch_page(url)

    if homepage.error:
        save_stage_result(db, job_id, "website_verification", "Uncertain", "Low", 10,
                          data={"error": homepage.error, "url": url},
                          evidence=[{"source": "fetch", "url": url, "note": homepage.error}])
        return "ERROR"

    score = 25.0  # Base score for reachable live homepage (HTTP 200)
    signals = {"live_site_reachable": True}
    evidence = [{"source": "fetch", "url": url, "note": "Homepage verified & reachable"}]
    name = company.name
    norm = normalize_company_name(name)

    # Domain similarity & brand token matching
    dn = domain_to_name(company.domain)
    clean_domain = re.sub(r"[^a-z0-9]", "", dn.lower())
    clean_name = re.sub(r"[^a-z0-9]", "", norm.lower())
    dsim = name_similarity(norm, dn)

    if clean_domain in clean_name or clean_name in clean_domain or dsim > 0.4:
        score += W["domain_similarity"]
        signals["domain_similarity"] = True
        evidence.append({"source": "domain_match", "note": f"Domain '{company.domain}' matches company identity"})

    # Flexible Title Match
    title_lower = homepage.title.lower()
    if norm in title_lower or clean_domain in title_lower or dsim > 0.4:
        score += W["title_match"]
        signals["title_match"] = True

    # Meta Description Match
    meta_lower = homepage.meta_description.lower()
    if norm in meta_lower or clean_domain in meta_lower:
        score += W["meta_match"]
        signals["meta_match"] = True

    # Body Text Match
    body_lower = homepage.body_text.lower()
    if norm in body_lower or clean_domain in body_lower:
        score += W["body_text_match"]
        signals["body_text_match"] = True

    # About Page
    about = find_about_page(url, homepage)
    if about and not about.error:
        score += W["about_page_match"]
        signals["about_page_exists"] = True
        evidence.append({"source": "fetch", "url": about.url, "note": "About page verified"})

    # Contact Page
    contact = find_contact_page(url, homepage)
    if contact and not contact.error:
        score += W["contact_page_exists"]
        signals["contact_page_exists"] = True

    # Social links
    if homepage.social_links:
        score += W["social_links"]
        signals["social_links"] = list(homepage.social_links.keys())

    # Footer Copyright
    footer_text = body_lower[-500:] if len(body_lower) > 500 else body_lower
    if "©" in footer_text or "copyright" in footer_text or "all rights reserved" in footer_text:
        score += W["footer_copyright"]
        signals["footer_copyright"] = True

    # Track if website is JS-rendered (used by downstream stages' fallback logic)
    signals["is_js_shell"] = homepage.is_js_shell

    score = min(score, 100.0)

    # Email domain hard filter: Only emails matching @verified_domain
    domain_clean = company.domain.lower().replace("www.", "").strip()
    raw_emails = list(set(
        (homepage.emails or []) +
        (about.emails if about and not about.error else []) +
        (contact.emails if contact and not contact.error else [])
    ))
    verified_emails = [
        e for e in raw_emails
        if e.lower().endswith("@" + domain_clean) or e.lower().endswith("." + domain_clean)
    ]

    # Phone number filter: filter out loose personal Indian mobile prefixes
    raw_phones = list(set(
        (homepage.phones or []) +
        (contact.phones if contact and not contact.error else [])
    ))
    company_phones = [
        p for p in raw_phones
        if not INDIAN_PERSONAL_MOBILE_RE.match(p.replace(" ", "").strip())
    ]

    save_stage_result(
        db, job_id, "website_verification",
        status_from_score(score), compute_label(score), round(score, 1),
        data={
            "url": url, "signals": signals,
            "social_links": homepage.social_links,
            "emails_found": verified_emails[:10],
            "phones_found": company_phones[:5],
        },
        evidence=evidence,
    )
    return "OK"
