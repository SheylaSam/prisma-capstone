"""Pydantic-Schemas für Universe-Endpoints (Request/Response DTOs)."""

from uuid import UUID

from pydantic import BaseModel, field_validator


class UniverseRead(BaseModel):
    """Serialisierungsschema für eine einzelne Universe-Entität."""

    id: UUID
    name: str
    region: str
    tickers: list[str]


class UniverseListResponse(BaseModel):
    """Wrapper für Universe-Listen mit Gesamtanzahl."""

    items: list[UniverseRead]
    total: int


class CreateUniverseRequest(BaseModel):
    """Request-Body für POST /api/v1/universes."""

    name: str
    region: str
    tickers: list[str]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name darf nicht leer sein")
        return v

    @field_validator("region")
    @classmethod
    def region_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("region darf nicht leer sein")
        return v

    @field_validator("tickers")
    @classmethod
    def tickers_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("tickers darf nicht leer sein")
        return [t.upper().strip() for t in v]


class SyncResponse(BaseModel):
    """Antwort auf POST /api/v1/universes/{id}/sync."""

    universe_id: UUID
    synced: int
