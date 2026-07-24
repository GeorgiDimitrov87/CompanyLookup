import json
import logging

import redis as redis_lib

from app.celery_app import celery
from app.config import settings
from app.db import SessionLocal
from app.pipeline import aggregator
from app.pipeline.stages import (
    company_discovery, contact_enrichment, founder_discovery,
    linkedin_discovery, meta_ads, social_presence, website_verification,
)
from app.pipeline.utils import save_stage_result

logger = logging.getLogger(__name__)
_redis = redis_lib.Redis.from_url(settings.REDIS_URL)


def _notify(job_id: str, stage: str, status: str, confidence: str):
    try:
        _redis.publish(f"job:{job_id}", json.dumps({
            "stage": stage, "status": status, "confidence": confidence,
        }))
    except Exception:
        pass


def _run_stage(stage_module, job_id: str, stage_name: str, **kwargs):
    db = SessionLocal()
    try:
        result = stage_module.run(job_id, db, **kwargs)
        from uuid import UUID
        from app.models.stage_result import StageResult
        sr = db.query(StageResult).filter_by(
            job_id=UUID(job_id) if isinstance(job_id, str) else job_id,
            stage=stage_name,
        ).first()
        if sr:
            _notify(job_id, stage_name, sr.status, sr.confidence)
        return result
    except Exception:
        logger.exception("Stage %s failed for job %s", stage_name, job_id)
        save_stage_result(db, job_id, stage_name, "Uncertain", "Low", 0,
                          data={"error": "Stage execution failed"},
                          evidence=[{"source": "pipeline", "note": "Internal error"}])
        _notify(job_id, stage_name, "Uncertain", "Low")
        return "ERROR"
    finally:
        db.close()


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def discover_company_task(self, job_id: str):
    result = _run_stage(company_discovery, job_id, "company_discovery")
    if result == "NEEDS_INPUT":
        _notify(job_id, "company_discovery", "NEEDS_INPUT", "Low")
        return
    if result == "FAILED":
        return
    verify_website_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def verify_website_task(self, job_id: str):
    _run_stage(website_verification, job_id, "website_verification")
    linkedin_discovery_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def linkedin_discovery_task(self, job_id: str):
    _run_stage(linkedin_discovery, job_id, "company_linkedin")
    founder_discovery_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def founder_discovery_task(self, job_id: str):
    _run_stage(founder_discovery, job_id, "founder_discovery")
    contact_enrichment_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def contact_enrichment_task(self, job_id: str):
    _run_stage(contact_enrichment, job_id, "contact_enrichment")
    social_presence_facebook_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def social_presence_facebook_task(self, job_id: str):
    _run_stage(social_presence, job_id, "facebook_presence", platform="facebook")
    social_presence_instagram_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def social_presence_instagram_task(self, job_id: str):
    _run_stage(social_presence, job_id, "instagram_presence", platform="instagram")
    meta_ads_task.delay(job_id)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def meta_ads_task(self, job_id: str):
    _run_stage(meta_ads, job_id, "meta_ads")
    aggregate_task.delay(job_id)


@celery.task(bind=True)
def aggregate_task(self, job_id: str):
    db = SessionLocal()
    try:
        aggregator.run(job_id, db)
        _notify(job_id, "_complete", "COMPLETE", "")
    except Exception:
        logger.exception("Aggregation failed for job %s", job_id)
    finally:
        db.close()
