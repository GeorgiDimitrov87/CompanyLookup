import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.pipeline.providers.meta_ads_provider import check_ads_api, check_ads_web_fallback
from app.pipeline.scoring import WEIGHTS, compute_label
from app.pipeline.utils import get_job, get_stage_data, save_stage_result, update_job_status

logger = logging.getLogger(__name__)
W = WEIGHTS["meta_ads"]


def run(job_id: str, db: Session) -> str:
    job = get_job(db, job_id)
    update_job_status(db, job_id, "RUNNING", "meta_ads")

    company = job.company
    if not company:
        save_stage_result(db, job_id, "meta_ads", "Not found", "Low", 0, data={}, evidence=[])
        return "NOT_FOUND"

    score = 0.0
    evidence = []
    ads = []
    check_time = datetime.now(timezone.utc).isoformat()

    # Get Facebook page URL if found
    fb_data = get_stage_data(db, job_id, "facebook_presence")
    fb_url = fb_data.get("profile_url") if fb_data else None

    # Primary: Official API (if token configured)
    if settings.META_AD_LIBRARY_TOKEN:
        result = check_ads_api(company.name, settings.META_AD_LIBRARY_TOKEN, fb_url)
        if result["found"]:
            ads = result["ads"]
            score += W["api_found"]
            evidence.append({"source": "meta_ad_library_api", "note": f"Found {len(ads)} active ad(s)"})
        else:
            evidence.append({"source": "meta_ad_library_api", "note": "No active ads found"})
    else:
        # Fallback: Web-based search
        result = check_ads_web_fallback(company.name, fb_url)
        if result["found"]:
            ads = result["ads"]
            score += W["web_fallback_found"]
            evidence.append({"source": "meta_ad_library_web", "note": f"Found {len(ads)} ad reference(s) (web fallback)"})
        else:
            evidence.append({"source": "meta_ad_library_web", "note": "No active ads found (web fallback)"})

    score = min(score, 100)

    if not ads:
        save_stage_result(
            db, job_id, "meta_ads", "Not found", "Low", round(score, 1),
            data={
                "ads": [], "check_timestamp": check_time,
                "note": "No active ads found at time of check. This does not prove the company never advertises.",
            },
            evidence=evidence,
        )
        return "NOT_FOUND"

    save_stage_result(
        db, job_id, "meta_ads",
        "Verified" if score >= 50 else "Likely",
        compute_label(score), round(score, 1),
        data={"ads": ads[:5], "check_timestamp": check_time},
        evidence=evidence,
    )
    return "OK"
