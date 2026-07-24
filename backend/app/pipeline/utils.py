import logging
import re
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.lookup_job import LookupJob
from app.models.stage_result import StageResult

logger = logging.getLogger(__name__)


def save_stage_result(db: Session, job_id, stage, status, confidence, confidence_score, data=None, evidence=None):
    job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
    existing = db.query(StageResult).filter_by(job_id=job_uuid, stage=stage).first()
    if existing:
        existing.status = status
        existing.confidence = confidence
        existing.confidence_score = confidence_score
        existing.data = data
        existing.evidence = evidence
    else:
        existing = StageResult(
            job_id=job_uuid, stage=stage, status=status,
            confidence=confidence, confidence_score=confidence_score,
            data=data, evidence=evidence,
        )
        db.add(existing)
    db.commit()
    return existing


def update_job_status(db: Session, job_id, status, current_stage=None, failure_reason=None):
    job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
    job = db.query(LookupJob).filter_by(id=job_uuid).first()
    job.status = status
    if current_stage:
        job.current_stage = current_stage
    if failure_reason:
        job.failure_reason = failure_reason
    db.commit()
    return job


def is_social_media_domain(domain: str) -> bool:
    """Check if domain is a social media platform."""
    social_domains = {
        "linkedin.com", "facebook.com", "instagram.com", "twitter.com", 
        "x.com", "youtube.com", "tiktok.com", "pinterest.com", 
        "reddit.com", "medium.com", "crunchbase.com"
    }
    domain_lower = domain.lower().replace("www.", "")
    return any(social in domain_lower for social in social_domains)


def resolve_company(db: Session, job, name, domain, location=None, industry=None):
    if is_social_media_domain(domain):
        logger.warning(f"Social media domain {domain} selected as company website - this may not be the actual company site")
    
    company = Company(name=name, domain=domain, location=location, industry=industry)
    db.add(company)
    db.flush()
    job.company_id = company.id
    db.commit()
    return company


def get_job(db: Session, job_id):
    job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
    return db.query(LookupJob).filter_by(id=job_uuid).first()


def get_stage_data(db: Session, job_id, stage: str) -> dict | None:
    job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
    result = db.query(StageResult).filter_by(job_id=job_uuid, stage=stage).first()
    return result.data if result and result.data else None


def normalize_company_name(name: str) -> str:
    """Normalize company name by stripping common business legal entity and industry suffixes."""
    name = name.lower().strip()
    # Strip common business entity suffixes
    suffixes = [
        " pvt ltd", " pvt. ltd.", " private limited", " limited", " ltd.", " ltd", 
        " llp", " llp.", " inc", " inc.", " llc", " corp", " corp.", " corporation", 
        " co", " co.", " company", " group", " holdings", " plc", " ventures",
        " solutions", " technologies", " tech", " services", " enterprises", " enterprise"
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_company_name(a), normalize_company_name(b)).ratio()


def domain_to_name(domain: str) -> str:
    domain = domain.lower().replace("www.", "")
    name = domain.split(".")[0]
    return re.sub(r"[^a-z0-9]", "", name)
