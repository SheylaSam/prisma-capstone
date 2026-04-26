"""Unit-Tests für CostTracker.check_cap, CostTracker.record und CostTracker.summary.

Spezifiziert in `docs/specs/2026-04-25-budget-cap.md` §5 + §9 + §10.2.

Boundary-Tests via Monkey-Patch von `_current_month_usd` —
keine echte DB nötig.
"""

import re
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from backend.application.services.cost_tracker import CostTracker
from backend.domain.errors import BudgetCapExceeded
from backend.infrastructure.persistence.models.llm_call_log import LLMCallLogORM

pytestmark = pytest.mark.unit


def _make_tracker(
    *,
    cap: str = "100.00",
    threshold: str = "0.95",
) -> CostTracker:
    """Hilft Boilerplate zu reduzieren — Session ist für check_cap unbenutzt
    (wir patchen `_current_month_usd`)."""
    return CostTracker(
        session=Mock(),
        cap_usd=Decimal(cap),
        threshold=Decimal(threshold),
    )


class TestCheckCap:
    async def test_below_threshold_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # cap=100, threshold=0.95 → Schwelle bei 95.00.
        # current 94.99 + estimate 0.01 = 95.00 → exakt an Schwelle, nicht >.
        tracker = _make_tracker()
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("94.99")),
        )
        await tracker.check_cap(estimated_usd=Decimal("0.01"))  # darf nicht werfen

    async def test_exactly_at_threshold_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tracker = _make_tracker()
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("95.00")),
        )
        # 95.00 + 0.00 = 95.00 → nicht > 95.00, also kein Fehler
        await tracker.check_cap(estimated_usd=Decimal("0.00"))

    async def test_just_above_threshold_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tracker = _make_tracker()
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("95.00")),
        )
        # 95.00 + 0.01 = 95.01 → > 95.00, Fehler
        with pytest.raises(BudgetCapExceeded):
            await tracker.check_cap(estimated_usd=Decimal("0.01"))

    async def test_far_above_threshold_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tracker = _make_tracker()
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("99.50")),
        )
        with pytest.raises(BudgetCapExceeded):
            await tracker.check_cap(estimated_usd=Decimal("0.60"))

    async def test_exception_carries_correct_amounts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tracker = _make_tracker()
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("99.50")),
        )
        with pytest.raises(BudgetCapExceeded) as exc_info:
            await tracker.check_cap(estimated_usd=Decimal("0.60"))
        assert exc_info.value.current_usd == Decimal("99.50")
        assert exc_info.value.attempted_usd == Decimal("0.60")
        assert exc_info.value.cap_usd == Decimal("100.00")

    async def test_custom_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        tracker = _make_tracker(threshold="0.50")
        monkeypatch.setattr(
            tracker,
            "_current_month_usd",
            AsyncMock(return_value=Decimal("50.00")),
        )
        # 50.00 + 0.01 = 50.01 → > 50.00, Fehler bei 50% threshold
        with pytest.raises(BudgetCapExceeded):
            await tracker.check_cap(estimated_usd=Decimal("0.01"))


class TestRecord:
    @pytest.fixture
    def captured_session(self) -> Mock:
        """Eine Mock-Session die alle .add()-Aufrufe in self.added aufzeichnet."""
        added: list[LLMCallLogORM] = []
        session = Mock()
        session.added = added
        session.add = lambda obj: added.append(obj)
        session.commit = AsyncMock()
        return session

    async def test_creates_log_entry_for_chat_model(
        self, captured_session: Mock
    ) -> None:
        tracker = CostTracker(
            session=captured_session,
            cap_usd=Decimal("100.00"),
        )
        await tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-6",
            feature="narrative_engine",
            input_tokens=1_000_000,
            output_tokens=500_000,
            request_id="msg_abc",
        )

        assert len(captured_session.added) == 1
        entry = captured_session.added[0]
        assert isinstance(entry, LLMCallLogORM)
        assert entry.provider == "anthropic"
        assert entry.model == "claude-sonnet-4-6"
        assert entry.feature == "narrative_engine"
        assert entry.input_tokens == 1_000_000
        assert entry.output_tokens == 500_000
        # 1M input @ $3 + 0.5M output @ $15 = 3.00 + 7.50 = 10.50
        assert entry.cost_usd == Decimal("10.50")
        assert entry.request_id == "msg_abc"
        captured_session.commit.assert_called_once()

    async def test_creates_log_entry_for_embed_model(
        self, captured_session: Mock
    ) -> None:
        tracker = CostTracker(
            session=captured_session,
            cap_usd=Decimal("100.00"),
        )
        await tracker.record(
            provider="voyage",
            model="voyage-3-large",
            feature="rag_ingestion",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        entry = captured_session.added[0]
        # 1M tokens @ $0.18/M = 0.18
        assert entry.cost_usd == Decimal("0.18")
        assert entry.provider == "voyage"

    async def test_request_id_defaults_to_none(self, captured_session: Mock) -> None:
        tracker = CostTracker(
            session=captured_session,
            cap_usd=Decimal("100.00"),
        )
        await tracker.record(
            provider="anthropic",
            model="claude-haiku-4-5",
            feature="test_feature",
            input_tokens=1000,
            output_tokens=1000,
        )
        assert captured_session.added[0].request_id is None


# ---------------------------------------------------------------------------
# Hilfsfunktion für Session-Mocks mit Ergebnisliste (FIFO)
# ---------------------------------------------------------------------------


def _make_session_with_results(*results: object) -> Mock:
    """Erstellt eine Mock-Session, deren .execute()-Aufrufe die übergebenen
    Ergebnisse der Reihe nach (FIFO) zurückgeben.

    Jedes result-Objekt wird direkt als Rückgabewert von await execute() gesetzt.
    """
    session = Mock()
    side_effects = list(results)
    execute_results = [AsyncMock(return_value=r) for r in side_effects]
    session.execute = Mock(
        side_effect=[r() for r in [lambda r=r: r for r in execute_results]]
    )

    async def _execute(query, params=None):
        # Gibt die nächste vorgefertigte Antwort zurück
        return session._execute_iter.__next__()

    session._execute_iter = iter(side_effects)
    session.execute = AsyncMock(side_effect=list(side_effects))
    return session


def _make_scalar_result(value: object) -> Mock:
    """Mock für .scalar_one()-fähige Execute-Antwort."""
    m = Mock()
    m.scalar_one = Mock(return_value=value)
    return m


def _make_fetchall_result(rows: list) -> Mock:
    """Mock für .fetchall()-fähige Execute-Antwort."""
    m = Mock()
    m.fetchall = Mock(return_value=rows)
    return m


def _make_row(
    **kwargs: object,
) -> Mock:
    """Erstellt einen Mock-Row der Attribute als kwargs unterstützt."""
    row = Mock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


# ---------------------------------------------------------------------------
# TestSummary
# ---------------------------------------------------------------------------


class TestSummary:
    def _make_tracker_with_session(
        self, session: Mock, cap: str = "100.00"
    ) -> CostTracker:
        return CostTracker(
            session=session,
            cap_usd=Decimal(cap),
            threshold=Decimal("0.95"),
        )

    async def test_returns_current_month_string_in_yyyy_mm_format(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """month-Feld muss dem Muster YYYY-MM entsprechen."""
        scalar_result = _make_scalar_result(Decimal("5.00"))
        model_rows = _make_fetchall_result([])
        feature_rows = _make_fetchall_result([])
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session)
        summary = await tracker.summary(last_n=10)
        assert re.match(r"^\d{4}-\d{2}$", summary.month)

    async def test_remaining_usd_is_cap_minus_current_when_under(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """remaining_usd = cap - current, wenn current < cap."""
        scalar_result = _make_scalar_result(Decimal("10.00"))
        model_rows = _make_fetchall_result([])
        feature_rows = _make_fetchall_result([])
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session, cap="100.00")
        summary = await tracker.summary(last_n=10)
        assert summary.remaining_usd == Decimal("90.00")

    async def test_remaining_usd_is_zero_when_overspent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """remaining_usd darf nicht negativ sein — Floor bei 0."""
        scalar_result = _make_scalar_result(Decimal("120.00"))
        model_rows = _make_fetchall_result([])
        feature_rows = _make_fetchall_result([])
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session, cap="100.00")
        summary = await tracker.summary(last_n=10)
        assert summary.remaining_usd == Decimal("0")

    async def test_by_model_sorted_by_cost_desc(self) -> None:
        """by_model-Liste muss nach cost_usd absteigend sortiert sein."""
        scalar_result = _make_scalar_result(Decimal("0.00"))
        model_rows = _make_fetchall_result(
            [
                _make_row(model="claude-haiku-4-5", calls=5, cost_usd="2.50"),
                _make_row(model="claude-sonnet-4-6", calls=3, cost_usd="8.00"),
                _make_row(model="voyage-3-large", calls=10, cost_usd="0.50"),
            ]
        )
        feature_rows = _make_fetchall_result([])
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session)
        summary = await tracker.summary(last_n=10)
        costs = [b.cost_usd for b in summary.by_model]
        assert costs == sorted(costs, reverse=True)
        assert len(summary.by_model) == 3

    async def test_by_feature_sorted_by_cost_desc(self) -> None:
        """by_feature-Liste muss nach cost_usd absteigend sortiert sein."""
        scalar_result = _make_scalar_result(Decimal("0.00"))
        model_rows = _make_fetchall_result([])
        feature_rows = _make_fetchall_result(
            [
                _make_row(feature="rag_ingestion", calls=2, cost_usd="1.00"),
                _make_row(feature="narrative_engine", calls=4, cost_usd="5.00"),
                _make_row(feature="screening", calls=1, cost_usd="0.10"),
            ]
        )
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session)
        summary = await tracker.summary(last_n=10)
        costs = [b.cost_usd for b in summary.by_feature]
        assert costs == sorted(costs, reverse=True)
        assert len(summary.by_feature) == 3

    async def test_last_calls_respects_last_n_param(self) -> None:
        """last_n=5 muss als bound-Parameter `limit=5` an session.execute übergeben werden."""
        scalar_result = _make_scalar_result(Decimal("0.00"))
        model_rows = _make_fetchall_result([])
        feature_rows = _make_fetchall_result([])
        last_rows = _make_fetchall_result([])

        session = Mock()
        session.execute = AsyncMock(
            side_effect=[scalar_result, model_rows, feature_rows, last_rows]
        )

        tracker = self._make_tracker_with_session(session)
        await tracker.summary(last_n=5)

        # Der vierte execute()-Aufruf (Index 3) ist der last_calls-Query.
        fourth_call = session.execute.call_args_list[3]
        # Zweites positionales Argument (oder kwargs) ist der params-Dict.
        args, kwargs = fourth_call
        params = args[1] if len(args) > 1 else kwargs.get("params", {})
        assert params == {"limit": 5}
