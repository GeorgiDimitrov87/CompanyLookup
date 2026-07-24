"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text()),
        sa.Column("location", sa.Text()),
        sa.Column("industry", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "lookup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("location_hint", sa.Text()),
        sa.Column("industry_hint", sa.Text()),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("current_stage", sa.Text()),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "job_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lookup_jobs.id"), nullable=False),
        sa.Column("company_name", sa.Text()),
        sa.Column("domain", sa.Text()),
        sa.Column("score", sa.Numeric()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("selected", sa.Boolean(), server_default="false"),
    )

    op.create_table(
        "stage_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lookup_jobs.id"), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric()),
        sa.Column("data", postgresql.JSONB()),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("job_id", "stage"),
    )

    op.create_index("idx_stage_results_job", "stage_results", ["job_id"])
    op.create_index("idx_stage_results_data_gin", "stage_results", ["data"], postgresql_using="gin", postgresql_ops={"data": "jsonb_path_ops"})
    op.create_index("idx_jobs_status", "lookup_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_jobs_status")
    op.drop_index("idx_stage_results_data_gin")
    op.drop_index("idx_stage_results_job")
    op.drop_table("stage_results")
    op.drop_table("job_candidates")
    op.drop_table("lookup_jobs")
    op.drop_table("companies")
