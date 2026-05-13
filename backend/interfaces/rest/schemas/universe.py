"""Pydantic-Schemas für Universe-Endpoints (Request/Response DTOs)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class UniverseCreateRequest(BaseModel):
    name: str
    region: str
    tickers: list[str]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name darf nicht leer sein")
        return v

    @field_validator("tickers")
    @classmethod
    def tickers_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("tickers darf nicht leer sein")
        return v


class UniverseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str
    tickers: list[str]


class UniverseListResponse(BaseModel):
    items: list[UniverseRead]
    total: int
