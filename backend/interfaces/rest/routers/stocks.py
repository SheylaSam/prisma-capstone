"""REST-Router für Stock-Endpunkte unter /api/v1/stocks."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.application.services.stock_service import StockService
from backend.domain.repositories.ranking_run_repository import RankingRunRepository
from backend.domain.repositories.stock_repository import StockRepository
from backend.interfaces.rest.dependencies import (
    get_ranking_run_repository,
    get_stock_repository,
    get_stock_service,
)
from backend.interfaces.rest.schemas.stock import (
    LatestRankingSnapshot,
    StockFactsheet,
    StockListResponse,
    StockRead,
)

router = APIRouter(prefix="/api/v1", tags=["stocks"])


@router.get(
    "/stocks",
    response_model=StockListResponse,
    summary="Alle Stocks auflisten",
    description="Gibt eine paginierte Liste aller im System bekannten Stocks zurück.",
)
async def list_stocks(
    limit: int = Query(default=50, ge=1, le=200, description="Maximale Anzahl Ergebnisse"),
    offset: int = Query(default=0, ge=0, description="Anzahl zu überspringender Einträge"),
    service: StockService = Depends(get_stock_service),
) -> StockListResponse:
    stocks = await service.list_stocks(limit=limit, offset=offset)
    items = [StockRead.model_validate(stock) for stock in stocks]
    return StockListResponse(items=items, total=len(items))


@router.get(
    "/stocks/{ticker}/factsheet",
    response_model=StockFactsheet,
    summary="Stock-Factsheet abrufen",
    description="Gibt Stammdaten und neueste Ranking-Momentaufnahme für einen Ticker zurück.",
)
async def get_factsheet(
    ticker: str,
    stock_repo: StockRepository = Depends(get_stock_repository),
    run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
) -> StockFactsheet:
    stock = await stock_repo.get_by_ticker(ticker)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Stock '{ticker.upper()}' not found")
    raw = await run_repo.get_latest_ticker_result(ticker)
    snapshot = LatestRankingSnapshot.model_validate(raw) if raw is not None else None
    return StockFactsheet(stock=StockRead.model_validate(stock), latest_ranking=snapshot)
