"""UniverseService — Use-Case-Orchestrierung für Universe-CRUD."""

import uuid
from dataclasses import dataclass, field

from backend.domain.entities.universe import Universe
from backend.domain.ports.fundamentals_provider import FundamentalsProvider
from backend.domain.ports.market_data_provider import MarketDataProvider
from backend.domain.repositories.universe_repository import UniverseRepository


class UniverseNotFound(Exception):
    pass


@dataclass
class UniverseSyncResult:
    universe_id: uuid.UUID
    synced_count: int
    failed_tickers: list[str] = field(default_factory=list)


class UniverseService:
    """Kapselt die Geschäftslogik rund um Universe-Operationen.

    Kennt nur den abstrakten UniverseRepository-Port.
    """

    def __init__(self, repository: UniverseRepository) -> None:
        self._repository = repository

    async def list_universes(self) -> list[Universe]:
        return await self._repository.list()

    async def get_universe(self, universe_id: uuid.UUID) -> Universe:
        result = await self._repository.get(universe_id)
        if result is None:
            raise UniverseNotFound(f"Universum {universe_id} nicht gefunden")
        return result

    async def create_universe(
        self,
        name: str,
        region: str,
        tickers: list[str],
    ) -> Universe:
        universe = Universe(
            id=uuid.uuid4(),
            name=name,
            region=region,
            tickers=tuple(tickers),
        )
        await self._repository.save(universe)
        return universe

    async def sync_universe(
        self,
        universe_id: uuid.UUID,
        fundamentals_provider: FundamentalsProvider,
        market_data_provider: MarketDataProvider,
    ) -> UniverseSyncResult:
        universe = await self.get_universe(universe_id)
        tickers = list(universe.tickers)
        failed: list[str] = []

        try:
            fundamentals = await fundamentals_provider.get_fundamentals(tickers)
        except Exception:
            fundamentals = {}

        try:
            prices = await market_data_provider.get_prices(tickers)
            price_tickers = set(prices.columns.tolist())
        except Exception:
            price_tickers = set()

        for ticker in tickers:
            has_fundamentals = ticker in fundamentals and any(
                v is not None for v in fundamentals[ticker].values()
            )
            has_prices = ticker in price_tickers
            if not has_fundamentals or not has_prices:
                failed.append(ticker)

        return UniverseSyncResult(
            universe_id=universe_id,
            synced_count=len(tickers) - len(failed),
            failed_tickers=failed,
        )
