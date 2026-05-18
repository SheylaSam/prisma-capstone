"""REST-Router für Universe-Endpunkte unter /api/v1/universes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.application.services.universe_service import UniverseNotFound, UniverseService
from backend.domain.ports.fundamentals_provider import FundamentalsProvider
from backend.domain.ports.market_data_provider import MarketDataProvider
from backend.interfaces.rest.dependencies import (
    get_fundamentals_provider,
    get_market_data_provider,
    get_universe_service,
)
from backend.interfaces.rest.schemas.universe import (
    UniverseCreateRequest,
    UniverseListResponse,
    UniverseRead,
    UniverseSyncResponse,
)

router = APIRouter(prefix="/api/v1/universes", tags=["universes"])


@router.get(
    "",
    response_model=UniverseListResponse,
    summary="Alle Universen auflisten",
)
async def list_universes(
    service: UniverseService = Depends(get_universe_service),
) -> UniverseListResponse:
    universes = await service.list_universes()
    items = [
        UniverseRead(id=u.id, name=u.name, region=u.region, tickers=list(u.tickers))
        for u in universes
    ]
    return UniverseListResponse(items=items, total=len(items))


@router.get(
    "/{universe_id}",
    response_model=UniverseRead,
    summary="Einzelnes Universum abrufen",
)
async def get_universe(
    universe_id: UUID,
    service: UniverseService = Depends(get_universe_service),
) -> UniverseRead:
    try:
        universe = await service.get_universe(universe_id)
    except UniverseNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UniverseRead(
        id=universe.id, name=universe.name, region=universe.region, tickers=list(universe.tickers)
    )


@router.post(
    "",
    status_code=201,
    response_model=UniverseRead,
    summary="Neues Universum anlegen",
)
async def create_universe(
    request: UniverseCreateRequest,
    service: UniverseService = Depends(get_universe_service),
) -> UniverseRead:
    universe = await service.create_universe(
        name=request.name,
        region=request.region,
        tickers=request.tickers,
    )
    return UniverseRead(
        id=universe.id, name=universe.name, region=universe.region, tickers=list(universe.tickers)
    )


@router.post(
    "/{universe_id}/sync",
    response_model=UniverseSyncResponse,
    summary="Ticker-Daten für ein Universum synchronisieren",
)
async def sync_universe(
    universe_id: UUID,
    service: UniverseService = Depends(get_universe_service),
    fundamentals: FundamentalsProvider = Depends(get_fundamentals_provider),
    market_data: MarketDataProvider = Depends(get_market_data_provider),
) -> UniverseSyncResponse:
    try:
        result = await service.sync_universe(
            universe_id=universe_id,
            fundamentals_provider=fundamentals,
            market_data_provider=market_data,
        )
    except UniverseNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UniverseSyncResponse(
        universe_id=result.universe_id,
        synced_count=result.synced_count,
        failed_tickers=result.failed_tickers,
    )
