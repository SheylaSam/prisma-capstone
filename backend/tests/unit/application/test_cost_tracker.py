"""Unit-Tests für CostTracker.check_cap und CostTracker.record.

Spezifiziert in `docs/specs/2026-04-25-budget-cap.md` §5 + §10.2.

Boundary-Tests via Monkey-Patch von `_current_month_usd` —
keine echte DB nötig.
"""

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
