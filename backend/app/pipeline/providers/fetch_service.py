import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

SOCIAL_DOMAINS = {
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CompanyIntelBot/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"[\+]?[\d\s\-\(\)]{7,15}")


@dataclass
class PageData:
    url: str
    status_code: int = 0
    title: str = ""
    meta_description: str = ""
    body_text: str = ""
    links: list[dict] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    is_js_shell: bool = False
    error: str | None = None


def _is_retryable_status(status_code: int) -> bool:
    return status_code >= 500 or status_code == 429


def fetch_page(url: str, max_retries: int = 2) -> PageData:
    page = PageData(url=url)
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(
                timeout=settings.FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=HEADERS
            ) as http:
                resp = http.get(url)
                page.status_code = resp.status_code
                
                if resp.status_code >= 400:
                    if _is_retryable_status(resp.status_code) and attempt < max_retries - 1:
                        last_error = f"HTTP {resp.status_code}"
                        backoff = 0.5 * (2 ** attempt)
                        logger.warning(
                            "Fetch HTTP %d for %s (attempt %d/%d), retrying in %.1fs",
                            resp.status_code, url, attempt + 1, max_retries, backoff
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        page.error = f"HTTP {resp.status_code}"
                        return page
                
                html = resp.text
                break
                
        except httpx.HTTPStatusError as e:
            last_error = str(e)
            if _is_retryable_status(e.response.status_code) and attempt < max_retries - 1:
                backoff = 0.5 * (2 ** attempt)
                logger.warning(
                    "Fetch HTTP %d for %s (attempt %d/%d), retrying in %.1fs",
                    e.response.status_code, url, attempt + 1, max_retries, backoff
                )
                time.sleep(backoff)
            else:
                logger.error("Fetch HTTP %d not retryable for %s: %s", e.response.status_code, url, str(e))
                page.error = str(last_error)
                return page
                
        except (httpx.TimeoutException, httpx.ConnectError, ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                backoff = 0.5 * (2 ** attempt)
                logger.warning(
                    "Fetch failed for %s (attempt %d/%d), retrying in %.1fs: %s",
                    url, attempt + 1, max_retries, backoff, str(e)
                )
                time.sleep(backoff)
            else:
                logger.error("Fetch failed after %d attempts for %s: %s", max_retries, url, str(e))
                page.error = str(last_error)
                return page
        except Exception as e:
            page.error = str(e)
            return page
    else:
        page.error = str(last_error)
        return page

    soup = BeautifulSoup(html, "lxml")
    page.title = (soup.title.string.strip() if soup.title and soup.title.string else "")

    meta = soup.find("meta", attrs={"name": "description"})
    page.meta_description = meta.get("content", "").strip() if meta else ""

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    page.body_text = soup.get_text(separator=" ", strip=True)

    page.is_js_shell = len(page.body_text) < 200 and bool(
        soup.find("div", id=re.compile(r"^(root|app|__next)$"))
    )

    base_netloc = urlparse(url).netloc
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith(("http", "/")):
            abs_url = urljoin(url, href)
            page.links.append({"href": abs_url, "text": text})
            netloc = urlparse(abs_url).netloc.lower().replace("www.", "")
            for sd, platform in SOCIAL_DOMAINS.items():
                if sd in netloc:
                    page.social_links[platform] = abs_url

    page.emails = list(set(EMAIL_RE.findall(html)))
    raw_phones = PHONE_RE.findall(page.body_text)
    page.phones = [p.strip() for p in raw_phones if len(re.sub(r"\D", "", p)) >= 7][:5]

    return page


def fetch_subpage(base_url: str, paths: list[str]) -> PageData | None:
    for path in paths:
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        page = fetch_page(url)
        if not page.error and page.status_code < 400:
            return page
    return None


def find_about_page(base_url: str, homepage: PageData) -> PageData | None:
    base_netloc = urlparse(base_url).netloc
    for link in homepage.links:
        lower_href = link["href"].lower()
        lower_text = link["text"].lower()
        if any(k in lower_href or k in lower_text for k in ("about", "about-us", "team", "our-story")):
            if urlparse(link["href"]).netloc == base_netloc:
                return fetch_page(link["href"])
    return fetch_subpage(base_url, ["/about", "/about-us", "/team"])


def find_contact_page(base_url: str, homepage: PageData) -> PageData | None:
    base_netloc = urlparse(base_url).netloc
    for link in homepage.links:
        lower_href = link["href"].lower()
        lower_text = link["text"].lower()
        if any(k in lower_href or k in lower_text for k in ("contact", "contact-us", "get-in-touch")):
            if urlparse(link["href"]).netloc == base_netloc:
                return fetch_page(link["href"])
    return fetch_subpage(base_url, ["/contact", "/contact-us"])


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url
