"""FastAPI Dependency-Injection-Kette: Session → Repository → Service."""

import hmac
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.services.cost_tracker import CostTracker
from backend.application.services.stock_service import StockService
from backend.config import get_settings
from backend.domain.repositories.stock_repository import StockRepository
from backend.infrastructure.persistence.repositories.stock_repository import (
    SQLAStockRepository,
)
from backend.infrastructure.persistence.session import get_async_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Liefert eine AsyncSession für den aktuellen Request-Scope."""
    async for session in get_async_session():
        yield session


async def get_stock_repository(
    session: AsyncSession = Depends(get_session),
) -> StockRepository:
    """Instanziiert den SQLAlchemy-Adapter mit der aktuellen Session."""
    return SQLAStockRepository(session=session)


async def get_stock_service(
    repository: StockRepository = Depends(get_stock_repository),
) -> StockService:
    """Erstellt einen StockService mit dem injizierten Repository."""
    return StockService(repository=repository)


async def get_cost_tracker(
    session: AsyncSession = Depends(get_session),
) -> CostTracker:
    """Konstruiert einen CostTracker mit Settings-gespeisten Cap-Werten."""
    settings = get_settings()
    return CostTracker(
        session=session,
        cap_usd=settings.budget_cap_usd,
        threshold=settings.budget_cap_threshold,
    )


async def require_admin_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Vergleicht den eingehenden X-API-Key konstant-zeitsicher mit Settings.api_key.

    Fehlendes oder falsches Header liefert 401 (nicht 422), damit kein
    Information-Leak über die erwartete Header-Struktur entsteht.
    """
    settings = get_settings()
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
