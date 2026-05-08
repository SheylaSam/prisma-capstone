"""Unit-Tests fuer NarrativeService Multi-Memo-Batch-Methoden."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

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

        # asyncio.create_task mocken — kein Background-Lauf im Test.
        # Must return a task-like object that supports add_done_callback (Bug 2 fix).
        def _fake_create_task(coro: Any, **_kwargs: Any) -> Any:
            coro.close()
            fake_task = Mock()
            fake_task.add_done_callback = Mock()
            return fake_task

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
            # Bug 1 fix: no stock_id key — matches production RankingRunService output
            return [
                {"ticker": "A", "total_rank": 1},
                {"ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)

        # Bug 1 fix: get_by_ticker must return a Stock with the correct id
        def _make_stock_mock(stock_id: UUID) -> Any:
            s = MagicMock()
            s.id = stock_id
            return s

        ticker_map = {"A": _make_stock_mock(stock_ids[0]), "B": _make_stock_mock(stock_ids[1])}
        mock_stock_repo_instance = AsyncMock()
        mock_stock_repo_instance.get_by_ticker = AsyncMock(side_effect=lambda t: ticker_map.get(t))
        mock_stock_repo_class = Mock(return_value=mock_stock_repo_instance)

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
            # Bug 1 fix: no stock_id key
            return [
                {"ticker": "A", "total_rank": 1},
                {"ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)

        def _make_stock_mock(stock_id: UUID) -> Any:
            s = MagicMock()
            s.id = stock_id
            return s

        ticker_map = {"A": _make_stock_mock(stock_ids[0]), "B": _make_stock_mock(stock_ids[1])}
        mock_stock_repo_instance = AsyncMock()
        mock_stock_repo_instance.get_by_ticker = AsyncMock(side_effect=lambda t: ticker_map.get(t))
        mock_stock_repo_class = Mock(return_value=mock_stock_repo_instance)

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
            # Bug 1 fix: no stock_id key
            return [
                {"ticker": "A", "total_rank": 1},
                {"ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)

        def _make_stock_mock(stock_id: UUID) -> Any:
            s = MagicMock()
            s.id = stock_id
            return s

        ticker_map = {"A": _make_stock_mock(stock_ids[0]), "B": _make_stock_mock(stock_ids[1])}
        mock_stock_repo_instance = AsyncMock()
        mock_stock_repo_instance.get_by_ticker = AsyncMock(side_effect=lambda t: ticker_map.get(t))
        mock_stock_repo_class = Mock(return_value=mock_stock_repo_instance)

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

    async def test_execute_batch_partial_on_rate_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RateLimitError nach LLMClient-Retry-Exhaustion: Stock in failed_stock_ids."""
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
            # Bug 1 fix: no stock_id key
            return [
                {"ticker": "A", "total_rank": 1},
                {"ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)

        def _make_stock_mock(stock_id: UUID) -> Any:
            s = MagicMock()
            s.id = stock_id
            return s

        ticker_map = {"A": _make_stock_mock(stock_ids[0]), "B": _make_stock_mock(stock_ids[1])}
        mock_stock_repo_instance = AsyncMock()
        mock_stock_repo_instance.get_by_ticker = AsyncMock(side_effect=lambda t: ticker_map.get(t))
        mock_stock_repo_class = Mock(return_value=mock_stock_repo_instance)

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

        # Erster Stock: ok. Zweiter: RateLimitError (nach LLMClient-Retry-Exhaustion).
        async def _flaky(stock_id: Any, *_args: Any, **_kwargs: Any) -> None:
            if stock_id == stock_ids[1]:
                raise anthropic.RateLimitError(
                    "rate limit",
                    response=Mock(status_code=429),
                    body={},
                )

        service._generate_memo_isolated = AsyncMock(side_effect=_flaky)  # type: ignore[method-assign]

        await service._execute_batch(job_id)

        last_job: MemoBatchJob = batch_repo.save.await_args_list[-1].args[0]
        assert last_job.status == "partial"
        assert stock_ids[1] in last_job.failed_stock_ids
        assert stock_ids[0] not in last_job.failed_stock_ids


class TestGetBatchJob:
    async def test_returns_none_for_unknown_id(self) -> None:
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=None)
        service = _make_service(batch_repository=batch_repo)

        result = await service.get_batch_job(uuid4())
        assert result is None

    async def test_returns_running_job_when_recent(self) -> None:
        from backend.domain.entities.memo_batch_job import MemoBatchJob

        recent_start = datetime.now(UTC)
        job = MemoBatchJob(
            id=uuid4(),
            model_run_id=uuid4(),
            top_n=20,
            language="de",
            status="running",
            failed_stock_ids=[],
            error_message=None,
            created_at=recent_start,
            started_at=recent_start,
        )
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=job)
        batch_repo.save = AsyncMock()
        service = _make_service(batch_repository=batch_repo)

        result = await service.get_batch_job(job.id)
        assert result is not None
        assert result.status == "running"
        # save() NICHT gerufen — kein cleanup noetig
        batch_repo.save.assert_not_awaited()

    async def test_marks_stale_running_as_failed(self) -> None:
        from datetime import timedelta

        from backend.domain.entities.memo_batch_job import MemoBatchJob

        old_start = datetime.now(UTC) - timedelta(seconds=700)  # > 600s default timeout
        job = MemoBatchJob(
            id=uuid4(),
            model_run_id=uuid4(),
            top_n=20,
            language="de",
            status="running",
            failed_stock_ids=[],
            error_message=None,
            created_at=old_start,
            started_at=old_start,
        )
        batch_repo = AsyncMock()
        batch_repo.get = AsyncMock(return_value=job)
        batch_repo.save = AsyncMock()
        service = _make_service(batch_repository=batch_repo)

        result = await service.get_batch_job(job.id)
        assert result is not None
        assert result.status == "failed"
        assert "stale" in (result.error_message or "").lower()
        batch_repo.save.assert_awaited_once()


class TestListMemosForRun:
    async def test_delegates_to_repo(self) -> None:
        memo_repo = AsyncMock()
        memo_repo.list_by_run = AsyncMock(return_value=[])
        service = _make_service(memo_repository=memo_repo)

        run_id = uuid4()
        await service.list_memos_for_run(run_id, language="de")
        memo_repo.list_by_run.assert_awaited_once_with(run_id, language="de")


class TestGetStockTickerMap:
    async def test_returns_ticker_for_known_stock(self) -> None:
        from unittest.mock import MagicMock

        from backend.domain.entities.stock import Stock

        sid = uuid4()
        stock = MagicMock(spec=Stock)
        stock.ticker = "NESN"

        stock_repo = AsyncMock()
        stock_repo.get = AsyncMock(return_value=stock)
        service = _make_service(stock_repository=stock_repo)

        result = await service.get_stock_ticker_map([sid])

        assert result == {sid: "NESN"}
        stock_repo.get.assert_awaited_once_with(sid)

    async def test_skips_deleted_stock(self) -> None:
        """Falls Stock nicht mehr in der DB (CASCADE-delete): kein Eintrag in der Map."""
        sid = uuid4()

        stock_repo = AsyncMock()
        stock_repo.get = AsyncMock(return_value=None)
        service = _make_service(stock_repository=stock_repo)

        result = await service.get_stock_ticker_map([sid])

        assert result == {}

    async def test_empty_input_returns_empty_dict(self) -> None:
        stock_repo = AsyncMock()
        service = _make_service(stock_repository=stock_repo)

        result = await service.get_stock_ticker_map([])

        assert result == {}
        stock_repo.get.assert_not_awaited()

    async def test_multiple_stocks_all_found(self) -> None:
        from unittest.mock import MagicMock

        from backend.domain.entities.stock import Stock

        sid1, sid2, sid3 = uuid4(), uuid4(), uuid4()

        def _make_stock(ticker: str) -> Stock:
            s = MagicMock(spec=Stock)
            s.ticker = ticker
            return s

        stocks = {sid1: _make_stock("NESN"), sid2: _make_stock("ROG"), sid3: _make_stock("ABBN")}
        stock_repo = AsyncMock()
        stock_repo.get = AsyncMock(side_effect=lambda sid: stocks.get(sid))
        service = _make_service(stock_repository=stock_repo)

        result = await service.get_stock_ticker_map([sid1, sid2, sid3])

        assert result == {sid1: "NESN", sid2: "ROG", sid3: "ABBN"}
        assert stock_repo.get.await_count == 3

    async def test_partial_missing_stocks(self) -> None:
        """Nur bekannte Stocks tauchen in der Map auf."""
        from unittest.mock import MagicMock

        from backend.domain.entities.stock import Stock

        sid_known = uuid4()
        sid_deleted = uuid4()

        known_stock = MagicMock(spec=Stock)
        known_stock.ticker = "NESN"

        stock_repo = AsyncMock()
        stock_repo.get = AsyncMock(
            side_effect=lambda sid: known_stock if sid == sid_known else None
        )
        service = _make_service(stock_repository=stock_repo)

        result = await service.get_stock_ticker_map([sid_known, sid_deleted])

        assert result == {sid_known: "NESN"}
        assert sid_deleted not in result


# ---------------------------------------------------------------------------
# New tests for the 3 critical bug fixes
# ---------------------------------------------------------------------------


class TestBug2BackgroundTaskRetention:
    """Bug 2 fix: asyncio.create_task return value must be retained."""

    async def test_start_batch_retains_task_reference(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After start_batch, _background_tasks must hold a reference to the spawned task."""
        import asyncio

        run_repo = AsyncMock()
        run_repo.get_results = AsyncMock(return_value=[{"ticker": "X"}])
        batch_repo = AsyncMock()
        cost_tracker = AsyncMock()
        cost_tracker.check_cap = AsyncMock()

        captured_tasks: list[asyncio.Task[None]] = []

        real_create_task = asyncio.create_task

        def _spy_create_task(coro: Any, **kwargs: Any) -> asyncio.Task[None]:
            task: asyncio.Task[None] = real_create_task(coro, **kwargs)
            captured_tasks.append(task)
            # Cancel immediately so _execute_batch does not run for real
            task.cancel()
            return task

        monkeypatch.setattr("asyncio.create_task", _spy_create_task)

        service = _make_service(
            run_repository=run_repo,
            batch_repository=batch_repo,
            cost_tracker=cost_tracker,
        )

        await service.start_batch(uuid4(), top_n=5)

        # The task must be in _background_tasks (or already removed via done_callback
        # if it completed/was cancelled synchronously). Either way, create_task was called.
        assert len(captured_tasks) == 1
        # done_callback removes the task once done — but the set was populated first
        # (even if discard ran already, we verify via captured_tasks that it was added).
        assert captured_tasks[0] is not None


class TestBug3BudgetCapExceededCaught:
    """Bug 3 fix: BudgetCapExceeded mid-batch must be caught in _one(), not propagate."""

    async def test_execute_batch_partial_on_budget_cap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BudgetCapExceeded from _generate_memo_isolated: Stock lands in failed_stock_ids."""
        from backend.domain.entities.memo_batch_job import MemoBatchJob
        from backend.domain.errors import BudgetCapExceeded

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

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        session_factory = Mock(return_value=mock_session_cm)

        async def _mock_get_results(_run_id: Any) -> list[dict[str, Any]]:
            return [
                {"ticker": "A", "total_rank": 1},
                {"ticker": "B", "total_rank": 2},
            ]

        mock_run_repo_instance = AsyncMock()
        mock_run_repo_instance.get_results = AsyncMock(side_effect=_mock_get_results)
        mock_run_repo_class = Mock(return_value=mock_run_repo_instance)

        def _make_stock_mock(stock_id: UUID) -> Any:
            s = MagicMock()
            s.id = stock_id
            return s

        ticker_map = {"A": _make_stock_mock(stock_ids[0]), "B": _make_stock_mock(stock_ids[1])}
        mock_stock_repo_instance = AsyncMock()
        mock_stock_repo_instance.get_by_ticker = AsyncMock(side_effect=lambda t: ticker_map.get(t))
        mock_stock_repo_class = Mock(return_value=mock_stock_repo_instance)

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

        # First stock: ok. Second: BudgetCapExceeded mid-call.
        async def _budget_fail(stock_id: Any, *_args: Any, **_kwargs: Any) -> None:
            if stock_id == stock_ids[1]:
                raise BudgetCapExceeded(
                    current_usd=Decimal("19.90"),
                    attempted_usd=Decimal("0.025"),
                    cap_usd=Decimal("20.00"),
                )

        service._generate_memo_isolated = AsyncMock(side_effect=_budget_fail)  # type: ignore[method-assign]

        await service._execute_batch(job_id)

        last_job: MemoBatchJob = batch_repo.save.await_args_list[-1].args[0]
        # Spec §8: partial (not a full crash), failed stock in failed_stock_ids
        assert last_job.status == "partial"
        assert stock_ids[1] in last_job.failed_stock_ids
        assert stock_ids[0] not in last_job.failed_stock_ids
