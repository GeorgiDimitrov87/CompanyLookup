import logging
import re
from collections import defaultdict
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import settings
from app.models.job_candidate import JobCandidate
from app.pipeline.providers.searxng_client import searxng
from app.pipeline.scoring import compute_label, corroboration_bonus
from app.pipeline.utils import (
    domain_to_name, get_job, name_similarity, normalize_company_name,
    resolve_company, save_stage_result, update_job_status,
)

logger = logging.getLogger(__name__)

SUBPAGE_TITLE_WORDS = {
    "our products", "products", "careers", "about us", "contact us",
    "home", "services", "privacy policy", "terms of service", "blog",
    "news", "team", "features", "pricing", "solutions", "dashboard",
}

SOCIAL_DOMAINS = {"linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com"}

# Third-party company-database / directory / aggregator sites. These often
# have a page literally titled with the exact company name (e.g. Tracxn's
# "{Company} — Legal Entity" listing page), so title-match alone can score
# deceptively high — but the domain itself is never the company's OWN
# website. These are never allowed to become the resolved company.domain
# (that would silently poison every downstream stage — verification,
# LinkedIn, founder, contact would all end up describing the directory
# instead of the company). They're still useful, though — for companies
# with no findable official site, a directory listing is real evidence of
# the company's NAME and existence, so they're used as a fallback signal
# for identification only, never for the website itself. See Tier 2 below.
DIRECTORY_DOMAINS = {
    "tracxn.com", "crunchbase.com", "zoominfo.com", "owler.com", "dnb.com",
    "bloomberg.com", "glassdoor.com", "indeed.com", "pitchbook.com",
    "craft.co", "rocketreach.co", "apollo.io", "wikipedia.org",
    "wellfound.com", "angel.co", "builtwith.com", "similarweb.com",
    "opencorporates.com", "zaubacorp.com", "tofler.in", "indiamart.com",
    "justdial.com", "sulekha.com", "mca.gov.in", "signalhire.com",
    "lusha.com", "clutch.co", "g2.com", "capterra.com", "trustpilot.com",
}

NOISE_SUBDOMAINS = {
    "www", "en", "in", "us", "uk", "m", "shop", "blog", "app", "mail",
    "support", "help", "docs", "news", "store",
}

MIN_SIGNAL_TO_QUALIFY = 0.30
MIN_CANDIDATE_SCORE = 30.0
MIN_NAME_FRAGMENT_SIM = 0.35

# Directory-sourced identification is inherently weaker evidence than a
# real, independently-verifiable website — capped below "High" regardless
# of how strong the title match looks, since there's no first-party site to
# actually verify anything against.
DIRECTORY_CONFIDENCE_CAP = 55.0


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "company_discovery")

    queries = [f'"{job.company_name}"', job.company_name]
    if job.location_hint:
        queries.append(f'"{job.company_name}" "{job.location_hint}"')
    if job.industry_hint:
        queries.append(f'"{job.company_name}" {job.industry_hint}')

    all_results = []
    for q in queries:
        all_results.extend(searxng.search(q, num_results=15))

    official_domains, directory_domains = _group_by_domain(all_results)

    # Tier 1: official, company-owned domains — always preferred when found.
    official_candidates = _rank_candidates(
        official_domains, job.company_name, job.location_hint, job.industry_hint, use_domain_signal=True,
    )

    if official_candidates:
        return _resolve_from_candidates(db, job, official_candidates)

    # Tier 2: no official site found anywhere in results — fall back to a
    # directory/aggregator listing for NAME identification only. The
    # resolved company gets NO domain, so website_verification correctly
    # reports "Not found" downstream rather than treating the directory as
    # the company's own site.
    directory_candidates = _rank_candidates(
        directory_domains, job.company_name, job.location_hint, job.industry_hint, use_domain_signal=False,
    )

    if directory_candidates:
        top = directory_candidates[0]
        capped_score = min(top["score"], DIRECTORY_CONFIDENCE_CAP)
        resolve_company(db, job, top["name"], None, job.location_hint, job.industry_hint)
        save_stage_result(
            db, job_id, "company_discovery", "Likely", compute_label(capped_score), capped_score,
            data={"name": top["name"], "domain": None},
            evidence=top["evidence"] + [{
                "source": "pipeline",
                "note": f"No official website found. Company identified via third-party directory listing ({top['domain']}); website verification will be skipped.",
            }],
        )
        return "RESOLVED"

    update_job_status(db, job_id, "FAILED", failure_reason="company_not_found")
    save_stage_result(
        db, job_id, "company_discovery", "Not found", "Low", 0,
        data={"reason": "No plausible company found"},
        evidence=[{"source": "searxng", "note": "No usable results"}],
    )
    return "FAILED"


def _resolve_from_candidates(db: Session, job, candidates: list[dict]) -> str:
    top = candidates[0]
    threshold = settings.DISAMBIGUATION_SCORE_THRESHOLD
    ambiguous = len(candidates) > 1 and (top["score"] - candidates[1]["score"]) < threshold

    if ambiguous:
        for c in candidates[:10]:
            db.add(JobCandidate(
                job_id=job.id, company_name=c["name"],
                domain=c["domain"], score=c["score"], reasoning=c["reasoning"],
            ))
        db.commit()
        update_job_status(db, job.id, "NEEDS_INPUT", "company_discovery")
        return "NEEDS_INPUT"

    resolve_company(db, job, top["name"], top["domain"], job.location_hint, job.industry_hint)
    save_stage_result(
        db, job.id, "company_discovery", "Verified", compute_label(top["score"]), top["score"],
        data={"name": top["name"], "domain": top["domain"]},
        evidence=top["evidence"],
    )
    return "RESOLVED"


def _registrable_domain(netloc: str) -> str:
    netloc = netloc.lower()
    parts = netloc.split(".")
    if len(parts) > 2 and parts[0] in NOISE_SUBDOMAINS:
        return ".".join(parts[1:])
    return netloc


def _group_by_domain(results: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    official: dict[str, list[dict]] = defaultdict(list)
    directory: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        url = r.get("url", "")
        parsed = urlparse(url)
        domain = _registrable_domain(parsed.netloc)
        if not domain or domain in SOCIAL_DOMAINS:
            continue
        if domain in DIRECTORY_DOMAINS:
            directory[domain].append(r)
        else:
            official[domain].append(r)
    return official, directory


def _clean_company_title(title: str, query_name: str, domain: str) -> tuple[str | None, float]:
    dn = domain_to_name(domain)
    parts = [p.strip() for p in re.split(r"[\-|–—:]", title) if p.strip()]

    best_part = None
    best_sim = -1.0
    for part in parts:
        part_clean = part.lower()
        if part_clean in SUBPAGE_TITLE_WORDS or "dashboard" in part_clean:
            continue
        sim = max(name_similarity(query_name, part), name_similarity(dn, part))
        if sim > MIN_NAME_FRAGMENT_SIM and sim > best_sim:
            best_part = part
            best_sim = sim

    return best_part, best_sim


def _rank_candidates(
    domain_groups: dict[str, list[dict]],
    company_name: str,
    location: str | None,
    industry: str | None,
    use_domain_signal: bool,
) -> list[dict]:
    candidates = []
    norm_name = normalize_company_name(company_name)

    for domain, hits in domain_groups.items():
        evidence = []

        dn = domain_to_name(domain)
        domain_sim = 0.0
        if use_domain_signal:
            domain_sim = name_similarity(norm_name, dn)
            clean_dom = dn.lower().replace(" ", "")
            clean_query = norm_name.lower().replace(" ", "")
            # Only auto-boost on a substring match if the shared token is
            # long enough to be meaningful (short fragments prove nothing).
            if len(clean_dom) >= 4 and (clean_dom in clean_query or clean_query in clean_dom):
                domain_sim = max(domain_sim, 0.9)

        best_name = dn.capitalize() if dn else company_name
        best_name_sim = name_similarity(company_name, best_name)

        max_title_sim = 0.0
        for h in hits:
            title = h.get("title", "")
            sim = name_similarity(company_name, title)
            if sim > max_title_sim:
                max_title_sim = sim

            fragment, fragment_sim = _clean_company_title(title, company_name, domain)
            if fragment and fragment_sim > best_name_sim:
                best_name = fragment
                best_name_sim = fragment_sim

            evidence.append({"source": "searxng", "url": h.get("url"), "note": f"Title match: {sim:.0%}"})

        # Relevance gate: for official-domain scoring, require SOME real
        # signal (domain OR title). For directory-domain scoring, domain
        # similarity is meaningless by definition (the directory's own
        # domain will never resemble the company name), so gate on title
        # match alone.
        gate_signal = max(domain_sim, max_title_sim) if use_domain_signal else max_title_sim
        if gate_signal < MIN_SIGNAL_TO_QUALIFY:
            continue

        score = (domain_sim * 45 + max_title_sim * 35) if use_domain_signal else (max_title_sim * 70)

        if location:
            combined = " ".join(h.get("content", "") for h in hits)
            if location.lower() in combined.lower():
                score += 10
                evidence.append({"source": "searxng", "note": f"Location '{location}' found in search results"})

        if industry:
            combined = " ".join(h.get("content", "") for h in hits)
            if industry.lower() in combined.lower():
                score += 10

        sources = [h.get("engine", "unknown") for h in hits]
        score += corroboration_bonus(sources)

        score = min(score, 100.0)
        if score < MIN_CANDIDATE_SCORE:
            continue

        reasoning = f"Name similarity: {name_similarity(company_name, best_name):.0%}, Domain: {domain}, Hits: {len(hits)}"
        candidates.append({
            "name": best_name, "domain": domain, "score": round(score, 1),
            "reasoning": reasoning, "evidence": evidence,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates
