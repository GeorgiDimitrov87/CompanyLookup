import logging
import re
from sqlalchemy.orm import Session

from app.pipeline.providers.fetch_service import fetch_page, find_about_page, normalize_url
from app.pipeline.providers.searxng_client import searxng
from app.pipeline.scoring import WEIGHTS, compute_label
from app.pipeline.utils import domain_to_name, get_job, get_stage_data, name_similarity, save_stage_result, update_job_status

logger = logging.getLogger(__name__)
W = WEIGHTS["founder_discovery"]

TITLE_PRIORITY = ["founder", "co-founder", "ceo", "owner", "managing director", "president", "cto", "director"]

JUNK_NAME_WORDS = {
    "com", "led", "full", "culture", "team", "teams", "remote", "engineering",
    "fmcg", "innovation", "product", "products", "company", "inc", "llc", "ltd",
    "http", "https", "www", "activity", "downloads", "circuit", "video",
}

TITLE_PREFIX_PATTERN = re.compile(
    r"^(founder|co-founder|ceo|owner|director|president|cto|cfo|people|managing director|manager|lead|mr|mrs|ms|dr)\s+",
    re.IGNORECASE,
)
TITLE_SUFFIX_PATTERN = re.compile(
    r"\s+(founder|co-founder|ceo|owner|director|president|cto|cfo|co|manager|lead)$",
    re.IGNORECASE,
)

# Section headings that reliably introduce a team/leadership listing — the
# positional fallback only ever looks INSIDE the text window right after
# one of these, never across the whole page. This is what keeps it from
# picking up unrelated marketing copy as if it were a person's name.
TEAM_SECTION_ANCHORS = [
    "meet the team", "meet our team", "our team", "our founders",
    "leadership team", "the team behind", "who we are", "our leadership",
]

# How far past the anchor heading to scan for names — wide enough to cover
# a handful of team cards, narrow enough to stay out of unrelated content.
TEAM_SECTION_WINDOW_CHARS = 600

NAME_SHAPE_RE = re.compile(r"[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?")

# Positional matches are a weaker signal than an explicit "Name, Title"
# pair — this factor discounts them relative to W["website_about"], and
# _corroboration_score's SINGLE_SOURCE_CAP additionally keeps a
# positional-only result out of the "High" confidence band entirely.
POSITIONAL_WEIGHT_FACTOR = 0.5

# A single source (e.g. the website About page alone) is capped below the
# "High" confidence band even at its best-scoring mention — High is reserved
# for candidates corroborated by at least one INDEPENDENT source type
# (website + a LinkedIn search hit, for example). This matches ADR 06's
# intent, which the previous raw-sum scoring didn't actually enforce.
SINGLE_SOURCE_CAP = 70.0
CORROBORATION_BONUS = 30.0


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "founder_discovery")

    company = job.company
    if not company:
        save_stage_result(db, job_id, "founder_discovery", "Not found", "Low", 0, data={}, evidence=[])
        return "NOT_FOUND"

    candidates = []
    evidence = []

    # Get company linkedin URL context if available
    linkedin_data = get_stage_data(db, job_id, "company_linkedin")
    company_linkedin_url = linkedin_data.get("linkedin_url") if linkedin_data else None
    linkedin_matched_brand = linkedin_data.get("matched_brand") if linkedin_data else None

    # Check if website was JS-rendered
    is_js_restricted = False
    website_data = get_stage_data(db, job_id, "website_verification")
    if website_data and website_data.get("signals", {}).get("is_js_shell"):
        is_js_restricted = True
        evidence.append({
            "source": "pipeline",
            "note": "Website is JS-rendered, limited text extraction. Relying on search fallback.",
        })

    # Source 1: Website About Page
    url = website_data.get("url") if website_data else None
    if url and not is_js_restricted:
        homepage = fetch_page(url)
        about = find_about_page(url, homepage)
        target_page = about if (about and not about.error) else homepage

        people = _extract_people(target_page.body_text)
        for p in people:
            candidates.append({
                "name": p["name"],
                "title": p["title"],
                "source": "website_about",
                "score": W["website_about"],
            })
            evidence.append({
                "source": "website_about",
                "url": target_page.url,
                "note": f"Found {p['name']} ({p['title']}) on site",
            })

        # Positional fallback: if no name-with-title pair was found (common
        # on team/founder pages laid out as photo+name cards with the role
        # elsewhere, not adjacent in the flattened text), fall back to "the
        # first few names listed under a Team/Founders heading are likely
        # the founder/leadership" — a real, commonly-true heuristic. Scoped
        # strictly to text right after a genuine team-section anchor (not
        # the whole page) so this doesn't reintroduce the marketing-copy
        # false-positive problem (e.g. "Access Valuation Multiples" reading
        # as a name on an unrelated page). Always labeled as an inferred,
        # unconfirmed role — never asserted as "Founder" outright.
        if not people:
            positional = _extract_positional_team_names(target_page.body_text)
            for idx, name in enumerate(positional):
                decay = [1.0, 0.85, 0.7][min(idx, 2)]
                candidates.append({
                    "name": name,
                    "title": "Team Member (role unconfirmed)",
                    "source": "website_team_position",
                    "score": W["website_about"] * POSITIONAL_WEIGHT_FACTOR * decay,
                })
                evidence.append({
                    "source": "website_team_position",
                    "url": target_page.url,
                    "note": f"'{name}' listed near top of team/founders section — role not explicitly stated, position inferred as likely leadership",
                })

    # Source 2: SearXNG search using valid site:linkedin.com operator with context.
    title_confirmed_found = any(c["source"] == "website_about" for c in candidates)
    if not title_confirmed_found or is_js_restricted:
        clean_brand = domain_to_name(company.domain) if company.domain else company.name
        queries = [
            f'site:linkedin.com "{company.name}" "Founder"',
            f'site:linkedin.com "{clean_brand}" "Founder"',
            f'site:linkedin.com "{company.name}" "CEO"',
        ]
        if company.domain:
            queries.append(f'site:linkedin.com "{company.domain}" "Founder"')
        # The company's confirmed LinkedIn page title is often the fuller,
        # more precise brand string (e.g. "Traveon Ventures" vs. the shorter
        # resolved company name "Traveon") — a person's profile is more
        # likely to say "Founder | Traveon Ventures" verbatim, so this is
        # worth its own query variants rather than relying on company.name
        # alone to happen to be a substring match.
        if linkedin_matched_brand and linkedin_matched_brand.lower() != company.name.lower():
            queries.append(f'site:linkedin.com/in "{linkedin_matched_brand}" "Founder"')
            queries.append(f'site:linkedin.com/in "{linkedin_matched_brand}" "CEO"')

        for q in queries:
            results = searxng.search(q, num_results=5)
            for r in results:
                title = r.get("title", "")
                r_url = r.get("url", "")
                if "/in/" not in r_url.lower():
                    continue
                person_name = _clean_person_name(title.split(" - ")[0].split(" | ")[0])
                if person_name:
                    candidates.append({
                        "name": person_name, "title": "Founder / CEO",
                        "source": "searxng_linkedin", "score": W["company_linkedin"],
                        "linkedin_url": r_url,
                    })
                    evidence.append({
                        "source": "searxng",
                        "url": r_url,
                        "note": f"Discovered {person_name} via LinkedIn search",
                    })

    if not candidates:
        if is_js_restricted:
            note = (
                "Website is JS-rendered so no text could be extracted, and no "
                "matching LinkedIn profile was found via search. LinkedIn "
                "individual profile pages (/in/...) are frequently not indexed "
                "by search engines, even when the profile is public — this is a "
                "known limitation of the free-tier search-only approach. "
                "Enabling paid LinkedIn enrichment (ENABLE_PAID_ENRICHMENT) can "
                "resolve this by querying the company's confirmed LinkedIn page "
                "directly for its listed leadership."
            )
        else:
            note = "No valid decision-maker name parsed"
        save_stage_result(db, job_id, "founder_discovery", "Not found", "Low", 0,
                          data={"primary": None, "also_mentioned": []},
                          evidence=[{"source": "pipeline", "note": note}])
        return "NOT_FOUND"

    ranked = _rank_and_dedupe(candidates)
    if not ranked:
        save_stage_result(db, job_id, "founder_discovery", "Not found", "Low", 0,
                          data={"primary": None, "also_mentioned": []},
                          evidence=[{"source": "pipeline", "note": "No valid decision-maker name parsed"}])
        return "NOT_FOUND"

    primary = ranked[0]
    also_mentioned = ranked[1:4]

    if not primary.get("linkedin_url") and company.name:
        primary["linkedin_url"] = _find_person_linkedin(primary["name"], company.name, company_linkedin_url)

    total_score = _corroboration_score(primary["name"], candidates)

    save_stage_result(
        db, job_id, "founder_discovery",
        "Confirmed" if total_score >= 60 else "Probable",
        compute_label(total_score), round(total_score, 1),
        data={
            "primary": {
                "name": primary["name"],
                "position": primary["title"],
                "linkedin_url": primary.get("linkedin_url"),
            },
            "also_mentioned": [
                {
                    "name": p["name"],
                    "position": p["title"],
                    "linkedin_url": p.get("linkedin_url"),
                }
                for p in also_mentioned
            ],
        },
        evidence=evidence[:10],
    )
    return "OK"


def _corroboration_score(primary_name: str, raw_candidates: list[dict]) -> float:
    """
    Confidence should reflect how many INDEPENDENT source types agree on this
    person, not how many times one source happened to mention them (e.g. the
    same About-page bio matching both a "Name, Title" and "Title, Name"
    regex pattern used to silently double-count as if it were two sources).

    - Best single-source mention sets the base score, capped below the High
      band (SINGLE_SOURCE_CAP) so "found on the website only" can never read
      as equivalent to a corroborated result.
    - If >= 2 distinct source types (e.g. website_about AND
      searxng_linkedin) both name this same person, that's real
      corroboration — award a bonus that can push the result into High.
    """
    norm = primary_name.strip().lower()
    matches = [c for c in raw_candidates if c["name"].strip().lower() == norm]
    if not matches:
        return 0.0

    base = max(c["score"] for c in matches)
    distinct_sources = {c["source"] for c in matches}

    if len(distinct_sources) >= 2:
        return min(base + CORROBORATION_BONUS, 100.0)
    return min(base, SINGLE_SOURCE_CAP)


def _clean_person_name(raw_name: str) -> str | None:
    cleaned = raw_name.strip()
    cleaned = TITLE_PREFIX_PATTERN.sub("", cleaned)
    cleaned = TITLE_SUFFIX_PATTERN.sub("", cleaned)
    cleaned = cleaned.strip()

    words = cleaned.split()
    if len(words) < 2 or len(words) > 4:
        return None

    for w in words:
        if w.lower() in JUNK_NAME_WORDS or len(w) < 2 or not w.isalpha():
            return None

    return " ".join(w.capitalize() for w in words)


def _extract_positional_team_names(text: str, max_names: int = 3) -> list[str]:
    """
    Finds a genuine "Team/Founders" section heading, then scans only the
    text window right after it for name-shaped fragments, in the order
    they appear. This backs the "the first person listed under Team is
    usually the founder/CEO" heuristic without scanning the whole page
    (which is what let unrelated marketing copy get mistaken for names
    before). Returns up to `max_names` distinct, cleaned names in order.
    """
    lower_text = text.lower()
    anchor_idx = None
    for anchor in TEAM_SECTION_ANCHORS:
        idx = lower_text.find(anchor)
        if idx != -1 and (anchor_idx is None or idx < anchor_idx):
            anchor_idx = idx + len(anchor)

    if anchor_idx is None:
        return []

    window = text[anchor_idx: anchor_idx + TEAM_SECTION_WINDOW_CHARS]

    names: list[str] = []
    seen = set()
    for match in NAME_SHAPE_RE.finditer(window):
        candidate = _clean_person_name(match.group(0))
        if not candidate:
            continue
        norm = candidate.lower()
        if norm in seen:
            continue
        seen.add(norm)
        names.append(candidate)
        if len(names) >= max_names:
            break

    return names


def _extract_people(text: str) -> list[dict]:
    people = []
    pattern1 = re.compile(
        r"([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)[\s,\-–—|:]+("
        + "|".join(TITLE_PRIORITY)
        + r")",
        re.IGNORECASE,
    )
    pattern2 = re.compile(
        r"("
        + "|".join(TITLE_PRIORITY)
        + r")[\s,\-–—|:]+([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)",
        re.IGNORECASE,
    )

    for match in pattern1.finditer(text):
        name = _clean_person_name(match.group(1))
        if name:
            people.append({"name": name, "title": match.group(2).strip().title()})

    for match in pattern2.finditer(text):
        name = _clean_person_name(match.group(2))
        if name:
            people.append({"name": name, "title": match.group(1).strip().title()})

    return people


def _rank_and_dedupe(candidates: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for c in candidates:
        clean_name = _clean_person_name(c["name"]) or c["name"]
        norm = clean_name.lower()
        if norm not in seen:
            seen.add(norm)
            c["name"] = clean_name
            unique.append(c)
    unique.sort(key=lambda x: x["score"], reverse=True)
    return unique


def _find_person_linkedin(person_name: str, company_name: str, company_linkedin_url: str | None = None) -> str | None:
    query = f'site:linkedin.com/in "{person_name}" "{company_name}"'
    if company_linkedin_url and "/company/" in company_linkedin_url:
        slug = company_linkedin_url.split("/company/")[-1].strip("/")
        query = f'site:linkedin.com/in "{person_name}" "{slug}"'

    results = searxng.search(query, num_results=5)
    for r in results:
        url = r.get("url", "")
        if "/in/" in url and name_similarity(person_name, r.get("title", "").split(" - ")[0]) > 0.4:
            return url
    return None
