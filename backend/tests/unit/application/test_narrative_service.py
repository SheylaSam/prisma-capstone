"""Unit-Tests fuer NarrativeService — Helpers + Service-Logik."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.application.services.narrative_service import (
    NarrativeService,
    UniverseContext,
    _build_universe_context,
    _extract_ranking_for_ticker,
)
from backend.domain.entities.research_memo import ResearchMemo

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _sample_results() -> list[dict[str, Any]]:
    """3-Stock-Mini-Universe."""
    return [
        {
            "ticker": "NESN",
            "total_rank": 1,
            "weighted_avg": 8.4,
            "is_sweet_spot": True,
            "per_model_ranks": {
                "quality_classic": 8,
                "alpha": 12,
                "trend_momentum": 25,
                "value_alpha_potential": 60,
                "diversification": 5,
            },
        },
        {
            "ticker": "ROG",
            "total_rank": 2,
            "weighted_avg": 12.0,
            "is_sweet_spot": False,
            "per_model_ranks": {
                "quality_classic": 15,
                "alpha": 20,
                "trend_momentum": 18,
                "value_alpha_potential": 22,
                "diversification": 10,
            },
        },
        {
            "ticker": "ABBN",
            "total_rank": 3,
            "weighted_avg": 25.0,
            "is_sweet_spot": False,
            "per_model_ranks": {
                "quality_classic": 30,
                "alpha": 28,
                "trend_momentum": 35,
                "value_alpha_potential": 18,
                "diversification": 14,
            },
        },
    ]


def test_extract_ranking_for_ticker_returns_dict() -> None:
    results = _sample_results()
    extracted = _extract_ranking_for_ticker(results, ticker="ROG")

    assert extracted["ticker"] == "ROG"
    assert extracted["total_rank"] == 2
    assert extracted["per_model_ranks"]["quality_classic"] == 15


def test_extract_ranking_for_ticker_raises_when_missing() -> None:
    results = _sample_results()
    with pytest.raises(KeyError):
        _extract_ranking_for_ticker(results, ticker="UNKNOWN")


def test_build_universe_context_computes_correct_metrics() -> None:
    results = _sample_results()
    ctx = _build_universe_context(results)

    assert isinstance(ctx, UniverseContext)
    assert ctx.n_stocks == 3
    assert ctx.median_rank == 2  # median of [1, 2, 3]
    # 20%-Quantile von [1,2,3] mit linear interpolation: 1 + 0.4*(2-1) = 1.4 → round to 1 (we use int)
    # but exact computation depends on implementation; assert reasonable bounds
    assert 1 <= ctx.top20_threshold <= 2


def test_build_universe_context_with_one_stock() -> None:
    """Edge case: Universe mit nur 1 Stock — median=top20=1."""
    results = [
        {
            "ticker": "NESN",
            "total_rank": 1,
            "weighted_avg": 1.0,
            "is_sweet_spot": True,
            "per_model_ranks": {},
        }
    ]
    ctx = _build_universe_context(results)
    assert ctx.n_stocks == 1
    assert ctx.median_rank == 1
    assert ctx.top20_threshold == 1


# ---------------------------------------------------------------------------
# Task 6 — NarrativeService.get_memo
# ---------------------------------------------------------------------------


def _sample_memo(stock_id: Any = None, run_id: Any = None) -> ResearchMemo:
    return ResearchMemo(
        id=uuid4(),
        stock_id=stock_id or uuid4(),
        model_run_id=run_id or uuid4(),
        language="de",
        created_at=datetime.now(tz=UTC),
        one_liner="Kurzfassung des Memos.",
        ranking_interpretation="x" * 120,
        sweet_spot=True,
        sweet_spot_explanation=None,
        contradictions=[],
        key_strengths=["Top 10% Quality"],
        key_risks=["Bewertungs-Multiples nicht im Modell"],
        confidence="high",
        model_version="claude-sonnet-4-6",
    )


async def test_get_memo_returns_existing() -> None:
    stock_id, run_id = uuid4(), uuid4()
    expected = _sample_memo(stock_id=stock_id, run_id=run_id)

    memo_repo = AsyncMock()
    memo_repo.get = AsyncMock(return_value=expected)

    service = NarrativeService(
        memo_repository=memo_repo,
        run_repository=AsyncMock(),
        stock_repository=AsyncMock(),
        llm_client=AsyncMock(),
        prompt_loader=AsyncMock(),
    )
    result = await service.get_memo(stock_id, run_id)

    assert result is expected
    memo_repo.get.assert_awaited_once_with(stock_id, run_id, language="de")


async def test_get_memo_returns_none_when_missing() -> None:
    memo_repo = AsyncMock()
    memo_repo.get = AsyncMock(return_value=None)

    service = NarrativeService(
        memo_repository=memo_repo,
        run_repository=AsyncMock(),
        stock_repository=AsyncMock(),
        llm_client=AsyncMock(),
        prompt_loader=AsyncMock(),
    )
    result = await service.get_memo(uuid4(), uuid4())

    assert result is None
