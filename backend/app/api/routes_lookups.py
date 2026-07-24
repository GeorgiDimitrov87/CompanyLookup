from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.job_candidate import JobCandidate
from app.models.lookup_job import LookupJob
from app.pipeline.scoring import compute_label
from app.pipeline.utils import resolve_company, save_stage_result
from app.schemas.lookup import (
    CandidateResponse, CandidateSelect, CompanyResponse, JobCreatedResponse,
    LookupCreate, LookupListResponse, LookupResponse, StageResultResponse,
)
from app.tasks.celery_tasks import discover_company_task, verify_website_task

router = APIRouter()


@router.post("/lookups", status_code=202, response_model=JobCreatedResponse)
def create_lookup(req: LookupCreate, db: Session = Depends(get_db)):
    job = LookupJob(
        company_name=req.company_name,
        location_hint=req.location,
        industry_hint=req.industry,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    discover_company_task.delay(str(job.id))
    return JobCreatedResponse(job_id=job.id, status=job.status)


@router.get("/lookups/{job_id}", response_model=LookupResponse)
def get_lookup(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(LookupJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stages = {
        sr.stage: StageResultResponse(
            stage=sr.stage, status=sr.status, confidence=sr.confidence,
            confidence_score=sr.confidence_score, data=sr.data,
            evidence=sr.evidence, created_at=sr.created_at,
        )
        for sr in job.stage_results
    }

    candidates = None
    if job.status == "NEEDS_INPUT":
        candidates = [
            CandidateResponse(
                id=c.id, company_name=c.company_name, domain=c.domain,
                score=c.score, reasoning=c.reasoning, selected=c.selected,
            )
            for c in job.candidates
        ]

    company = None
    if job.company:
        company = CompanyResponse(
            id=job.company.id, name=job.company.name, domain=job.company.domain,
            location=job.company.location, industry=job.company.industry,
        )

    return LookupResponse(
        job_id=job.id, status=job.status, current_stage=job.current_stage,
        company=company, stages=stages, candidates=candidates,
        created_at=job.created_at,
    )


@router.post("/lookups/{job_id}/select-candidate", status_code=202, response_model=JobCreatedResponse)
def select_candidate(job_id: UUID, req: CandidateSelect, db: Session = Depends(get_db)):
    job = db.query(LookupJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "NEEDS_INPUT":
        raise HTTPException(status_code=400, detail="Job not awaiting input")

    candidate = db.query(JobCandidate).filter_by(id=req.candidate_id, job_id=job_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.selected = True
    resolve_company(db, job, candidate.company_name, candidate.domain,
                    job.location_hint, job.industry_hint)

    job.status = "RUNNING"
    db.commit()

    save_stage_result(
        db, str(job.id), "company_discovery", "Verified",
        compute_label(float(candidate.score or 50)), float(candidate.score or 50),
        data={"name": candidate.company_name, "domain": candidate.domain, "selected_by_user": True},
        evidence=[{"source": "user_selection", "note": f"User selected: {candidate.company_name}"}],
    )

    verify_website_task.delay(str(job.id))
    return JobCreatedResponse(job_id=job.id, status="RUNNING")


@router.get("/lookups", response_model=list[LookupListResponse])
def list_lookups(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    jobs = db.query(LookupJob).order_by(LookupJob.created_at.desc()).offset(skip).limit(limit).all()
    return [
        LookupListResponse(job_id=j.id, company_name=j.company_name, status=j.status, created_at=j.created_at)
        for j in jobs
    ]
