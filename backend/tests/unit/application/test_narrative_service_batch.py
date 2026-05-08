"""Unit-Tests fuer NarrativeService Multi-Memo-Batch-Methoden."""

from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from backend.application.services.narrative_service import NarrativeService

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_service(**overrides: Any) -> NarrativeService:
    """Helper: NarrativeService mit AsyncMock-Defaults bauen."""
    defaults = {
        "memo_repository": AsyncMock(),
        "run_repository": AsyncMock(),
        "stock_repository": AsyncMock(),
        "batch_repository": AsyncMock(),
        "llm_client": AsyncMock(),
        "prompt_loader": AsyncMock(),
        "cost_tracker": AsyncMock(),
        "session_factory": Mock(),
        "max_concurrent_batch_workers": 3,
        "stale_batch_timeout_seconds": 600,
    }
    defaults.update(overrides)
    return NarrativeService(**defaults)  # type: ignore[arg-type]


class TestStartBatch:
    async def test_start_batch_creates_pending_job(self, monkeypatch: pytest.MonkeyPatch) -> None:
        run_repo = AsyncMock()
        run_repo.get_results = AsyncMock(return_value=[{"ticker": "X"}])  # run exists
        batch_repo = AsyncMock()
        cost_tracker = AsyncMock()
        cost_tracker.check_cap = AsyncMock()

        # asyncio.create_task mocken — kein Background-Lauf im Test
        def _fake_create_task(coro: Any) -> None:
            coro.close()
            return None

        monkeypatch.setattr("asyncio.create_task", _fake_create_task)

        service = _make_service(
            run_repository=run_repo,
            batch_repository=batch_repo,
            cost_tracker=cost_tracker,
        )
        run_id = uuid4()

        job = await service.start_batch(run_id, top_n=20)

        assert job.status == "pending"
        assert job.model_run_id == run_id
        assert job.top_n == 20
        assert job.language == "de"
        batch_repo.save.assert_awaited_once()

    async def test_start_batch_raises_for_en_language(self) -> None:
        service = _make_service()
        with pytest.raises(NotImplementedError, match="en"):
            await service.start_batch(uuid4(), language="en")

    async def test_start_batch_raises_404_when_run_missing(self) -> None:
        run_repo = AsyncMock()
        run_repo.get_results = AsyncMock(return_value=None)
        service = _make_service(run_repository=run_repo)

        with pytest.raises(LookupError, match="Run"):
            await service.start_batch(uuid4())

    async def test_start_batch_pre_checks_budget_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.domain.errors import BudgetCapExceeded

        run_repo = AsyncMock()
        run_repo.get_results = AsyncMock(return_value=[{"ticker": "X"}])
        cost_tracker = AsyncMock()
        cost_tracker.check_cap = AsyncMock(
            side_effect=BudgetCapExceeded(
                current_usd=__import__("decimal").Decimal("19.00"),
                attempted_usd=__import__("decimal").Decimal("0.50"),
                cap_usd=__import__("decimal").Decimal("20.00"),
            )
        )

        # asyncio.create_task irrelevant — exception fires before
        service = _make_service(run_repository=run_repo, cost_tracker=cost_tracker)

        with pytest.raises(BudgetCapExceeded):
            await service.start_batch(uuid4(), top_n=20)

    async def test_start_batch_validates_top_n_bounds(self) -> None:
        service = _make_service()

        with pytest.raises(ValueError, match="top_n"):
            await service.start_batch(uuid4(), top_n=0)
        with pytest.raises(ValueError, match="top_n"):
            await service.start_batch(uuid4(), top_n=101)
