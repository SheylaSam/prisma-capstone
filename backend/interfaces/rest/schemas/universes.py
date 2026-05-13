"""Pydantic-Schemas für /api/v1/universes."""

from uuid import UUID

from pydantic import BaseModel

from backend.domain.entities.universe import Universe


class PostUniverseRequest(BaseModel):
    name: str
    tickers: list[str]
    region: str


class UniverseResponse(BaseModel):
    id: UUID
    name: str
    tickers: list[str]
    region: str

    @classmethod
    def from_domain(cls, universe: Universe) -> "UniverseResponse":
        return cls(
            id=universe.id,
            name=universe.name,
            tickers=list(universe.tickers),
            region=universe.region,
        )
