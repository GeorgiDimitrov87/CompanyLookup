from sqlalchemy.orm import Session

from app.models.lookup_job import LookupJob
from app.models.stage_result import StageResult
from app.pipeline.scoring import compute_overall_confidence
from app.pipeline.utils import get_job


def run(job_id: str, db: Session) -> dict:
    job = get_job(db, job_id)
    results = db.query(StageResult).filter_by(job_id=job.id).all()

    # All 8 pipeline stages completed execution
    job.status = "COMPLETE"
    job.current_stage = None
    db.commit()

    overall_confidence = compute_overall_confidence(results)

    stages = {}
    for r in results:
        stages[r.stage] = {
            "status": r.status,
            "confidence": r.confidence,
            "confidence_score": float(r.confidence_score) if r.confidence_score else None,
            "data": r.data,
            "evidence": r.evidence,
        }

    report = {
        "job_id": str(job.id),
        "status": job.status,
        "overall_confidence": overall_confidence,
        "company": {
            "name": job.company.name,
            "domain": job.company.domain,
            "location": job.company.location,
            "industry": job.company.industry,
        } if job.company else None,
        "stages": stages,
    }

    return report
