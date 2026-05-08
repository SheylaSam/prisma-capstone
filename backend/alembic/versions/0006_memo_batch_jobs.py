"""create memo_batch_jobs

Revision ID: 0006_memo_batch_jobs
Revises: 0005
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers
revision: str = "0006_memo_batch_jobs"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memo_batch_jobs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "model_run_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ranking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("top_n", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "failed_stock_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("top_n BETWEEN 1 AND 100", name="ck_memo_batch_jobs_top_n"),
        sa.CheckConstraint("language IN ('de', 'en')", name="ck_memo_batch_jobs_language"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'complete', 'partial', 'failed')",
            name="ck_memo_batch_jobs_status",
        ),
    )
    op.create_index(
        "ix_memo_batch_jobs_model_run_id",
        "memo_batch_jobs",
        ["model_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_memo_batch_jobs_model_run_id", table_name="memo_batch_jobs")
    op.drop_table("memo_batch_jobs")
