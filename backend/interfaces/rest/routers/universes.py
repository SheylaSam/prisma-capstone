"""REST-Router für Universe-Endpoints unter /api/v1/universes."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.domain.entities.universe import Universe
from backend.domain.repositories.universe_repository import UniverseRepository
from backend.interfaces.rest.dependencies import get_universe_repository
from backend.interfaces.rest.schemas.universe import (
    CreateUniverseRequest,
    SyncResponse,
    UniverseListResponse,
    UniverseRead,
)

router = APIRouter(prefix="/api/v1/universes", tags=["universes"])


def _to_schema(universe: Universe) -> UniverseRead:
    return UniverseRead(
        id=universe.id,
        name=universe.name,
        region=universe.region,
        tickers=list(universe.tickers),
    )


@router.get("", response_model=UniverseListResponse)
async def list_universes(
    repo: UniverseRepository = Depends(get_universe_repository),
) -> UniverseListResponse:
    universes = await repo.list()
    items = [_to_schema(u) for u in universes]
    return UniverseListResponse(items=items, total=len(items))


@router.post("", status_code=201, response_model=UniverseRead)
async def create_universe(
    request: CreateUniverseRequest,
    repo: UniverseRepository = Depends(get_universe_repository),
) -> UniverseRead:
    universe = Universe(
        id=uuid4(),
        name=request.name,
        region=request.region,
        tickers=tuple(request.tickers),
    )
    await repo.save(universe)
    return _to_schema(universe)


@router.get("/{universe_id}", response_model=UniverseRead)
async def get_universe(
    universe_id: UUID,
    repo: UniverseRepository = Depends(get_universe_repository),
) -> UniverseRead:
    universe = await repo.get(universe_id)
    if universe is None:
        raise HTTPException(status_code=404, detail=f"Universe {universe_id} not found")
    return _to_schema(universe)


@router.post("/{universe_id}/sync", response_model=SyncResponse)
async def sync_universe(
    universe_id: UUID,
    repo: UniverseRepository = Depends(get_universe_repository),
) -> SyncResponse:
    universe = await repo.get(universe_id)
    if universe is None:
        raise HTTPException(status_code=404, detail=f"Universe {universe_id} not found")
    # Stub: keine echten Marktdaten-Provider in Phase 1 — gibt 0 synchronisierte Einträge zurück.
    return SyncResponse(universe_id=universe_id, synced=0)
