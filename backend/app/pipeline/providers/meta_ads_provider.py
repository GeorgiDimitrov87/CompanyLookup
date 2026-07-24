import logging

import httpx

from app.config import settings
from app.pipeline.providers.searxng_client import searxng

logger = logging.getLogger(__name__)

META_AD_LIBRARY_API = "https://graph.facebook.com/v18.0/ads_archive"


def check_ads_api(company_name: str, token: str, fb_page_url: str | None = None) -> dict:
    try:
        params = {
            "search_terms": company_name,
            "ad_reached_countries": '["US"]',
            "ad_active_status": "ACTIVE",
            "access_token": token,
            "fields": "ad_creative_bodies,ad_delivery_start_time,page_name,ad_snapshot_url",
            "limit": 5,
        }
        with httpx.Client(timeout=settings.FETCH_TIMEOUT_SECONDS) as http:
            resp = http.get(META_AD_LIBRARY_API, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [])

        if not data:
            return {"found": False, "ads": []}

        ads = []
        for ad in data[:5]:
            ads.append({
                "page_name": ad.get("page_name", ""),
                "ad_copy": (ad.get("ad_creative_bodies", [""])[0] if ad.get("ad_creative_bodies") else ""),
                "start_date": ad.get("ad_delivery_start_time", ""),
                "ad_library_url": ad.get("ad_snapshot_url", ""),
                "source": "official_api",
            })
        return {"found": True, "ads": ads}

    except Exception:
        logger.exception("Meta Ad Library API failed")
        return {"found": False, "ads": []}


def check_ads_web_fallback(company_name: str, fb_page_url: str | None = None) -> dict:
    results = searxng.search(f'"{company_name}" site:facebook.com/ads/library', num_results=5)

    if not results:
        results = searxng.search(f'"{company_name}" facebook ads active', num_results=5)

    ads = []
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        content = r.get("content", "")
        if "ads/library" in url or "ad library" in title.lower():
            ads.append({
                "page_name": company_name,
                "ad_copy": content[:200] if content else "",
                "start_date": "",
                "ad_library_url": url,
                "source": "web_fallback",
            })

    return {"found": bool(ads), "ads": ads}
