"""Unit-Tests fuer NarrativeService Multi-Memo-Batch-Methoden."""

from datetime import UTC, datetime
from decimal import Decimal
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
        run_repo = AsyncMock()
        service = _make_service(run_repository=run_repo)
        with pytest.raises(NotImplementedError, match="en"):
            await service.start_batch(uuid4(), language="en")
        run_repo.get_results.assert_not_awaited()

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
                current_usd=Decimal("19.00"),
                attempted_usd=Decimal("0.50"),
                cap_usd=Decimal("20.00"),
            )
        )

        # asyncio.create_task irrelevant — exception fires before
        service = _make_service(run_repository=run_repo, cost_tracker=cost_tracker)

        with pytest.raises(BudgetCapExceeded):
            await service.start_batch(uuid4(), top_n=20)

    async def test_start_batch_validates_top_n_bounds(self) -> None:
        run_repo = AsyncMock()
        service = _make_service(run_repository=run_repo)

        with pytest.raises(ValueError, match="top_n"):
            await service.start_batch(uuid4(), top_n=0)
        run_repo.get_results.assert_not_awaited()

        with pytest.raises(ValueError, match="top_n"):
            await service.start_batch(uuid4(), top_n=101)
        run_repo.get_results.assert_not_awaited()


class TestExecuteBatch:
    async def test_execute_batch_all_success_marks_complete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from backend.domain.entities.memo_batch_job import MemoBatchJob

        run_id = uuid4()
        job_id = uuid4()
        stock_ids = [uuid4(), uuid4()]

        existing_job = MemoBatchJob(
            id=job_id,
            model_run_id=run_id,
            top_n=2,
            language="de",
            status="pending",
            failed_stock_ids=[],
            error_message=None,
            created_at=datetime.now(UTC),
        )
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=existing_job)
        batch_repo.save = AsyncMock()

        # session_factory mock — gibt context manager zurueck
        mock_session = AsyncMock()
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        session_factory = Mock(return_value=mock_session_cm)

        async def _mock_get_results(_run_id: Any) -> list[dict[str, Any]]:
            return [
                {"stock_id": str(stock_ids[0]), "ticker": "A", "total_rank": 1},
                {"stock_id": str(stock_ids[1]), "ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)
        mock_stock_repo_class = Mock(return_value=AsyncMock())

        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLARankingRunRepository",
            mock_run_repo_class,
        )
        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLAStockRepository",
            mock_stock_repo_class,
        )

        service = _make_service(
            batch_repository=batch_repo,
            session_factory=session_factory,
        )
        # _generate_memo_isolated mocken — wir testen Worker-Loop, nicht Memo-Inhalt
        service._generate_memo_isolated = AsyncMock()  # type: ignore[method-assign]

        await service._execute_batch(job_id)

        # save() mind. 2x: status=running, status=complete
        assert batch_repo.save.await_count >= 2
        last_save_call = batch_repo.save.await_args_list[-1]
        last_job: MemoBatchJob = last_save_call.args[0]
        assert last_job.status == "complete"
        assert last_job.failed_stock_ids == []

    async def test_execute_batch_partial_on_network_fail(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import anthropic

        from backend.domain.entities.memo_batch_job import MemoBatchJob

        run_id = uuid4()
        job_id = uuid4()
        stock_ids = [uuid4(), uuid4()]

        existing_job = MemoBatchJob(
            id=job_id,
            model_run_id=run_id,
            top_n=2,
            language="de",
            status="pending",
            failed_stock_ids=[],
            error_message=None,
            created_at=datetime.now(UTC),
        )
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=existing_job)
        batch_repo.save = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        session_factory = Mock(return_value=mock_session_cm)

        async def _mock_get_results(_run_id: Any) -> list[dict[str, Any]]:
            return [
                {"stock_id": str(stock_ids[0]), "ticker": "A", "total_rank": 1},
                {"stock_id": str(stock_ids[1]), "ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)
        mock_stock_repo_class = Mock(return_value=AsyncMock())

        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLARankingRunRepository",
            mock_run_repo_class,
        )
        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLAStockRepository",
            mock_stock_repo_class,
        )

        service = _make_service(
            batch_repository=batch_repo,
            session_factory=session_factory,
        )

        # Erster Stock: ok. Zweiter: APITimeoutError.
        async def _flaky(stock_id: Any, *_args: Any, **_kwargs: Any) -> None:
            if stock_id == stock_ids[1]:
                raise anthropic.APITimeoutError(request=Mock())

        service._generate_memo_isolated = AsyncMock(side_effect=_flaky)  # type: ignore[method-assign]

        await service._execute_batch(job_id)

        last_job: MemoBatchJob = batch_repo.save.await_args_list[-1].args[0]
        assert last_job.status == "partial"
        assert stock_ids[1] in last_job.failed_stock_ids
        assert stock_ids[0] not in last_job.failed_stock_ids

    async def test_execute_batch_all_fail_marks_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import anthropic

        from backend.domain.entities.memo_batch_job import MemoBatchJob

        run_id = uuid4()
        job_id = uuid4()
        stock_ids = [uuid4(), uuid4()]

        existing_job = MemoBatchJob(
            id=job_id,
            model_run_id=run_id,
            top_n=2,
            language="de",
            status="pending",
            failed_stock_ids=[],
            error_message=None,
            created_at=datetime.now(UTC),
        )
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=existing_job)
        batch_repo.save = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        session_factory = Mock(return_value=mock_session_cm)

        async def _mock_get_results(_run_id: Any) -> list[dict[str, Any]]:
            return [
                {"stock_id": str(stock_ids[0]), "ticker": "A", "total_rank": 1},
                {"stock_id": str(stock_ids[1]), "ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)
        mock_stock_repo_class = Mock(return_value=AsyncMock())

        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLARankingRunRepository",
            mock_run_repo_class,
        )
        monkeypatch.setattr(
            "backend.application.services.narrative_service.SQLAStockRepository",
            mock_stock_repo_class,
        )

        service = _make_service(
            batch_repository=batch_repo,
            session_factory=session_factory,
        )
        service._generate_memo_isolated = AsyncMock(  # type: ignore[method-assign]
            side_effect=anthropic.APIConnectionError(request=Mock())
        )

        await service._execute_batch(job_id)

        last_job: MemoBatchJob = batch_repo.save.await_args_list[-1].args[0]
        assert last_job.status == "failed"
        assert len(last_job.failed_stock_ids) == 2
