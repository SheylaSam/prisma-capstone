"""UniverseService — verwaltet Universen (CRUD ohne Delete)."""

from __future__ import annotations

from uuid import uuid4

from backend.domain.entities.universe import Universe
from backend.domain.repositories.universe_repository import UniverseRepository


class UniverseService:
    def __init__(self, universe_repo: UniverseRepository) -> None:
        self._repo = universe_repo

    async def list(self) -> list[Universe]:
        return await self._repo.list()

    async def create(self, name: str, tickers: list[str], region: str) -> Universe:
        universe = Universe(id=uuid4(), name=name, tickers=tickers, region=region)
        await self._repo.save(universe)
        return universe
