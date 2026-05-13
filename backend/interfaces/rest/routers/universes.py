"""FastAPI-Router für /api/v1/universes."""

from fastapi import APIRouter, Depends

from backend.application.services.universe_service import UniverseService
from backend.interfaces.rest.dependencies import get_universe_service
from backend.interfaces.rest.schemas.universes import PostUniverseRequest, UniverseResponse

router = APIRouter(prefix="/api/v1/universes", tags=["universes"])


@router.get("", response_model=list[UniverseResponse])
async def list_universes(
    service: UniverseService = Depends(get_universe_service),
) -> list[UniverseResponse]:
    universes = await service.list()
    return [UniverseResponse.from_domain(u) for u in universes]


@router.post("", status_code=201, response_model=UniverseResponse)
async def create_universe(
    request: PostUniverseRequest,
    service: UniverseService = Depends(get_universe_service),
) -> UniverseResponse:
    universe = await service.create(
        name=request.name,
        tickers=request.tickers,
        region=request.region,
    )
    return UniverseResponse.from_domain(universe)
