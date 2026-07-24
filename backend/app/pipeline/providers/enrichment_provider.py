from abc import ABC, abstractmethod

from app.config import settings


class EnrichmentProvider(ABC):
    @abstractmethod
    def enrich_company(self, linkedin_url: str) -> dict | None:
        pass

    @abstractmethod
    def enrich_person(self, linkedin_url: str) -> dict | None:
        pass


class NoOpEnrichmentProvider(EnrichmentProvider):
    def enrich_company(self, linkedin_url: str) -> dict | None:
        return None

    def enrich_person(self, linkedin_url: str) -> dict | None:
        return None


class ProxycurlEnrichmentProvider(EnrichmentProvider):
    """Stub — activate by setting ENABLE_PAID_ENRICHMENT=true + PROXYCURL_API_KEY."""

    def enrich_company(self, linkedin_url: str) -> dict | None:
        return None

    def enrich_person(self, linkedin_url: str) -> dict | None:
        return None


def get_enrichment_provider() -> EnrichmentProvider:
    if settings.ENABLE_PAID_ENRICHMENT and settings.PROXYCURL_API_KEY:
        return ProxycurlEnrichmentProvider()
    return NoOpEnrichmentProvider()
