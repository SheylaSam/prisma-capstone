"""Request/Response-Schemas fuer Multi-Memo Batch-Endpoints.

Spec: docs/specs/2026-05-08-narrative-engine-multi-memo-batch.md §6.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BatchRequest(BaseModel):
    model_run_id: UUID
    top_n: int = Field(20, ge=1, le=100)
    language: Literal["de", "en"] = "de"


class BatchProgress(BaseModel):
    expected: int
    completed: int
    failed: int


class BatchMemoSummary(BaseModel):
    stock_id: UUID
    ticker: str
    one_liner: str
    is_error: bool


class BatchJobResponse(BaseModel):
    job_id: UUID
    model_run_id: UUID
    top_n: int
    language: Literal["de", "en"]
    status: Literal["pending", "running", "complete", "partial", "failed"]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    progress: BatchProgress
    failed_stock_ids: list[UUID]
    error_message: str | None
    memos: list[BatchMemoSummary]


class BatchJobAcceptedResponse(BaseModel):
    """202-Accepted-Response — schlanker als BatchJobResponse."""

    job_id: UUID
    model_run_id: UUID
    top_n: int
    language: Literal["de", "en"]
    status: Literal["pending"]
    created_at: datetime
