WEIGHTS = {
    "website_verification": {
        "title_match": 25, "meta_match": 15, "body_text_match": 15,
        "about_page_match": 15, "contact_page_exists": 10, "address_match": 10,
        "social_links": 15, "domain_similarity": 40, "footer_copyright": 10,
    },
    "company_linkedin": {
        "outbound_link": 75, "searxng_name_match": 35,
        "location_corroboration": 15, "domain_corroboration": 20,
    },
    "founder_discovery": {
        "website_about": 35, "company_linkedin": 30,
        "searxng_press": 20, "title_match": 15,
    },
    "contact_enrichment": {
        "published_email": 50, "pattern_corroborated": 25,
        "pattern_uncorroborated": 10, "published_phone": 15,
    },
    "social_presence": {
        "outbound_link": 75, "searxng_match": 35, "name_corroboration": 20,
    },
    "meta_ads": {
        "api_found": 50, "web_fallback_found": 35, "page_match": 15,
    },
}


def compute_label(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def corroboration_bonus(sources: list[str]) -> int:
    unique = len(set(sources))
    if unique >= 3:
        return 15
    if unique >= 2:
        return 10
    return 0


def compute_overall_confidence(stage_results: list) -> str:
    if not stage_results:
        return "Low"

    core_stages = {"website_verification", "company_discovery"}
    label_values = {"High": 3, "Medium": 2, "Low": 1}
    labels = []

    for sr in stage_results:
        if sr.stage in core_stages and sr.confidence == "Low":
            return "Low"
        labels.append(sr.confidence)

    avg = sum(label_values.get(l, 1) for l in labels) / len(labels)
    if avg >= 2.5:
        return "High"
    if avg >= 1.5:
        return "Medium"
    return "Low"


def status_from_score(score: float) -> str:
    if score >= 75:
        return "Verified"
    if score >= 45:
        return "Likely"
    return "Uncertain"
