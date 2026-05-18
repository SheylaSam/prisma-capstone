"""Pydantic-Schemas fuer RAG-Retrieval-Endpoint."""

from uuid import UUID

from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)
    ticker: str | None = Field(default=None, description="Optionaler Ticker-Filter (z.B. 'AAPL')")


class ChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_idx: int
    content: str
    similarity: float
    ticker: str
    doc_type: str


class RetrieveResponse(BaseModel):
    results: list[ChunkResponse]
    total: int
