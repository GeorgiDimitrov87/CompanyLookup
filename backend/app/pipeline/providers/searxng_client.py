import time
import hashlib
import json
import logging
from typing import Any

import httpx
import redis

from app.config import settings

logger = logging.getLogger(__name__)


class SearxngClient:
    def __init__(self):
        self.base_url = settings.SEARXNG_BASE_URL
        self.timeout = max(settings.FETCH_TIMEOUT_SECONDS, 25.0)
        self.cache = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.cache_ttl = settings.SEARXNG_CACHE_TTL_SECONDS
        self.max_retries = 2
        self.retry_backoff = 0.5

    def _cache_key(self, query: str, categories: str) -> str:
        raw = f"{query}|{categories}"
        return f"searxng:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code >= 500 or status_code == 429

    def _retry_with_backoff(self, func, *args, **kwargs) -> list[dict[str, Any]]:
        """
        Never raises — every branch resolves to a return. This is the contract
        every pipeline stage relies on (`results = searxng.search(...)` is
        always treated as a plain list). Unexpected/non-network errors are
        logged and treated as "no results" rather than propagated, same as
        the original behavior before retry support was added.
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if isinstance(result, list) and not result and attempt == 0:
                    backoff = self.retry_backoff
                    logger.warning(
                        "SearXNG returned empty results (attempt %d/%d), retrying in %.1fs",
                        attempt + 1, self.max_retries, backoff,
                    )
                    time.sleep(backoff)
                    continue
                return result
            except httpx.HTTPStatusError as e:
                last_error = e
                if self._is_retryable_status(e.response.status_code) and attempt < self.max_retries - 1:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        "SearXNG HTTP %d (attempt %d/%d), retrying in %.1fs",
                        e.response.status_code, attempt + 1, self.max_retries, backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error("SearXNG HTTP %d not retryable, giving up: %s", e.response.status_code, str(e))
                    return []
            except (httpx.TimeoutException, httpx.ConnectError, ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        "SearXNG request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, self.max_retries, backoff, str(e),
                    )
                    time.sleep(backoff)
                else:
                    logger.error("SearXNG request failed after %d attempts: %s", self.max_retries, str(e))
            except Exception:
                # Anything unexpected (bad JSON, Redis hiccup escaping the cache
                # try/except, etc.) — log it and degrade to empty results rather
                # than letting it crash the calling stage.
                logger.exception("Unexpected SearXNG error")
                return []
        return []

    def search(self, query: str, categories: str = "general", num_results: int = 10) -> list[dict[str, Any]]:
        key = self._cache_key(query, categories)
        try:
            cached = self.cache.get(key)
            if cached:
                data = json.loads(cached)
                if data:
                    return data
        except Exception:
            pass

        def _do_search():
            with httpx.Client(timeout=self.timeout) as http:
                resp = http.get(
                    f"{self.base_url}/search",
                    params={"q": query, "format": "json", "categories": categories},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])[:num_results]

                # ONLY cache non-empty results!
                if results:
                    try:
                        self.cache.setex(key, self.cache_ttl, json.dumps(results))
                    except Exception:
                        pass
                return results

        return self._retry_with_backoff(_do_search)

    def search_site(self, site: str, query: str, **kwargs) -> list[dict[str, Any]]:
        return self.search(f'site:{site} "{query}"', **kwargs)


searxng = SearxngClient()
