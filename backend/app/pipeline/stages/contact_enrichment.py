import logging
import re

import dns.resolver
from sqlalchemy.orm import Session

from app.pipeline.providers.searxng_client import searxng
from app.pipeline.scoring import WEIGHTS, compute_label
from app.pipeline.utils import domain_to_name, get_job, get_stage_data, save_stage_result, update_job_status

logger = logging.getLogger(__name__)
W = WEIGHTS["contact_enrichment"]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
INDIAN_PERSONAL_MOBILE_RE = re.compile(r"^\+?91[\s\-]?[789]\d{9}$")


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "contact_enrichment")

    company = job.company
    if not company:
        save_stage_result(db, job_id, "contact_enrichment", "Not found", "Low", 0,
                          data={}, evidence=[])
        return "NOT_FOUND"

    score = 0.0
    evidence = []
    data = {"emails": [], "phones": [], "email_status": "Not found", "phone_status": "Not found"}
    domain_clean = company.domain.lower().replace("www.", "").strip() if company.domain else ""

    # Tier 1: Collect published emails/phones from website verification
    website_data = get_stage_data(db, job_id, "website_verification")
    published_emails = website_data.get("emails_found", []) if website_data else []
    published_phones = website_data.get("phones_found", []) if website_data else []

    # Get founder info
    founder_data = get_stage_data(db, job_id, "founder_discovery")
    founder_name = None
    if founder_data and founder_data.get("primary"):
        founder_name = founder_data["primary"].get("name")

    # Web search fallback for published emails matching domain
    if not published_emails and domain_clean:
        search_res = searxng.search(f'"{domain_clean}" email', num_results=5)
        for r in search_res:
            content = r.get("content", "") + " " + r.get("title", "")
            found = EMAIL_REGEX.findall(content)
            for e in found:
                e_clean = e.lower()
                if (e_clean.endswith("@" + domain_clean) or e_clean.endswith("." + domain_clean)) and e_clean not in published_emails:
                    published_emails.append(e_clean)

    # Process emails (strict domain matching)
    if published_emails:
        valid_domain_emails = [
            e for e in published_emails
            if domain_clean and (e.lower().endswith("@" + domain_clean) or e.lower().endswith("." + domain_clean))
        ]
        for email in valid_domain_emails[:4]:
            tier = "Verified" if founder_name and _email_matches_person(email, founder_name) else "Probable"
            data["emails"].append({"email": email, "status": tier, "source": "website"})
        if data["emails"]:
            score += W["published_email"]
            data["email_status"] = "Verified" if any(e["status"] == "Verified" for e in data["emails"]) else "Probable"
            evidence.append({"source": "website", "note": f"Found {len(data['emails'])} verified email(s)"})

    # Tier 2: Pattern-guessed (if Tier 1 found no specific personal email)
    if not data["emails"] and founder_name and company.domain:
        guesses = _generate_email_patterns(founder_name, company.domain)
        has_mx = _check_mx(company.domain)

        if has_mx:
            for guess in guesses[:3]:
                data["emails"].append({"email": guess, "status": "Probable", "source": "pattern_guess"})

            score += W["pattern_corroborated"]
            data["email_status"] = "Probable"
            evidence.append({
                "source": "pattern_guess",
                "note": f"Pattern: first.last@{company.domain} (MX verified)",
            })

    # Phones (filter out loose personal Indian mobile numbers)
    clean_phones = [
        p for p in published_phones
        if not INDIAN_PERSONAL_MOBILE_RE.match(p.replace(" ", "").strip())
    ]
    if clean_phones:
        data["phones"] = [{"phone": p, "status": "Not verified", "source": "website"} for p in clean_phones[:3]]
        data["phone_status"] = "Not verified"
        score += W["published_phone"]
        evidence.append({"source": "website", "note": f"Found {len(clean_phones)} phone(s)"})

    score = min(score, 100.0)
    status = "Verified" if data["email_status"] == "Verified" else (
        "Probable" if data["email_status"] in ("Probable", "Unverified") else "Not found"
    )

    save_stage_result(
        db, job_id, "contact_enrichment", status, compute_label(score), round(score, 1),
        data=data, evidence=evidence,
    )
    return "OK"


def _generate_email_patterns(name: str, domain: str) -> list[str]:
    parts = name.lower().strip().split()
    if len(parts) < 2:
        return [f"{parts[0]}@{domain}"]
    first, last = parts[0], parts[-1]
    return [
        f"{first}.{last}@{domain}",
        f"{first}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"{first}{last}@{domain}",
    ]


def _check_mx(domain: str) -> bool:
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def _email_matches_person(email: str, person_name: str) -> bool:
    local = email.split("@")[0].lower()
    parts = person_name.lower().split()
    return any(p in local for p in parts if len(p) > 2)
