from abc import ABC, abstractmethod

from app.config import settings
from app.pipeline.providers.searxng_client import searxng
from app.pipeline.utils import name_similarity


class LinkedInProvider(ABC):
    @abstractmethod
    def find_company(self, company_name: str, domain: str | None = None) -> dict | None:
        pass

    @abstractmethod
    def find_person(self, person_name: str, company_name: str) -> dict | None:
        pass


class SearxngLinkedInProvider(LinkedInProvider):
    def find_company(self, company_name: str, domain: str | None = None) -> dict | None:
        results = searxng.search_site("linkedin.com/company", company_name, num_results=5)
        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            if "/company/" in url and name_similarity(company_name, title.split("|")[0]) > 0.4:
                return {"url": url, "title": title, "source": "searxng"}
        return None

    def find_person(self, person_name: str, company_name: str) -> dict | None:
        results = searxng.search(f'site:linkedin.com/in "{person_name}" "{company_name}"', num_results=5)
        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            if "/in/" in url and name_similarity(person_name, title.split("-")[0]) > 0.4:
                return {"url": url, "title": title, "source": "searxng"}
        return None


class ProxycurlLinkedInProvider(LinkedInProvider):
    """Stub — enabled only when ENABLE_PAID_ENRICHMENT=true and PROXYCURL_API_KEY is set."""

    def find_company(self, company_name: str, domain: str | None = None) -> dict | None:
        # TODO: Implement Proxycurl company lookup
        return None

    def find_person(self, person_name: str, company_name: str) -> dict | None:
        # TODO: Implement Proxycurl person lookup
        return None


def get_provider() -> LinkedInProvider:
    if settings.ENABLE_PAID_ENRICHMENT and settings.PROXYCURL_API_KEY:
        return ProxycurlLinkedInProvider()
    return SearxngLinkedInProvider()
