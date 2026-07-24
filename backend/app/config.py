from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://companyintel:companyintel@postgres:5432/company_intel"
    REDIS_URL: str = "redis://redis:6379/0"
    SEARXNG_BASE_URL: str = "http://searxng:8080"

    ENABLE_PAID_ENRICHMENT: bool = False
    PROXYCURL_API_KEY: str = ""
    META_AD_LIBRARY_TOKEN: str = ""

    FETCH_TIMEOUT_SECONDS: int = 10
    SEARXNG_CACHE_TTL_SECONDS: int = 3600
    DISAMBIGUATION_SCORE_THRESHOLD: int = 15

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
