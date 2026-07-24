from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class LookupCreate(BaseModel):
    company_name: str
    location: str | None = None
    industry: str | None = None


class CandidateSelect(BaseModel):
    candidate_id: UUID


class CandidateResponse(BaseModel):
    id: UUID
    company_name: str | None
    domain: str | None
    score: Decimal | None
    reasoning: str | None
    selected: bool

    model_config = {"from_attributes": True}


class StageResultResponse(BaseModel):
    stage: str
    status: str
    confidence: str
    confidence_score: Decimal | None = None
    data: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    domain: str | None
    location: str | None
    industry: str | None

    model_config = {"from_attributes": True}


class LookupResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str | None = None
    company: CompanyResponse | None = None
    stages: dict[str, StageResultResponse] = {}
    candidates: list[CandidateResponse] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class LookupListResponse(BaseModel):
    job_id: UUID
    company_name: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobCreatedResponse(BaseModel):
    job_id: UUID
    status: str
