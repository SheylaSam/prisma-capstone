"""E2E-Integrationstests für die Agentic-Pipeline — nur LLM gemockt, Verdrahtung echt.

Lehre aus V4.3: Unit-Tests waren grün weil sie MLFeatureService / SwissQuantScorer /
_normalize_weights komplett gemockt haben. Echter Agent-Run fand Bugs in:
  - Arg-Anzahl (z.B. messages_create-Kwargs)
  - Methodennamen (z.B. get_price_history statt get_history)
  - JSON-Serialisierung (Pydantic-Dataclass-Felder nicht serialisierbar)
  - Markdown-Stripping (LLM liefert ```json...``` statt reines JSON)

Diese Tests instantiieren die echten Services und mocken nur den HTTP/LLM-Layer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from backend.application.agents.portfolio_agent import PortfolioAgent
from backend.application.services.macro_service import MacroService
from backend.application.services.signal_aggregation_service import SignalAggregationService
from backend.domain.entities.swiss_stock import SwissStock
from backend.domain.value_objects.decision_signal import DecisionSignal
from backend.domain.value_objects.macro_context import MacroContext
from backend.domain.value_objects.swiss_fundamentals import SwissFundamentals

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_price_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"Close": closes, "Volume": 1_000_000}, index=pd.date_range("2025-01-01", periods=n))


def _make_fundamentals() -> SwissFundamentals:
    return SwissFundamentals(
        market_cap_chf=Decimal("250_000_000"),
        pe_ratio=15.0,
        pb_ratio=1.8,
        dividend_yield=0.025,
        eps_chf=12.0,
    )


def _make_swiss_stock(ticker: str = "NESN", market_cap: int = 250_000_000) -> SwissStock:
    return SwissStock(
        id=uuid4(),
        ticker=ticker,
        isin="CH0012221716",
        name=ticker,
        exchange="XSWX",
        sector=None,
        market_cap_chf=Decimal(market_cap),
    )


# ---------------------------------------------------------------------------
# SignalAggregationService — echte Verdrahtung, YFinance gemockt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signal_pipeline_real_wiring_buy_signal() -> None:
    """Prüft end-to-end: echte MLFeatureService+SwissQuantScorer, nur Adapter gemockt.

    Fängt: falscher Methodenname auf YFinanceAdapter, falsche Arg-Anzahl,
    fehlende SNB-Rate-Kompatibilität.
    """
    mock_adapter = AsyncMock()
    mock_adapter.get_fundamentals.return_value = _make_fundamentals()
    mock_adapter.get_price_history.return_value = _make_price_df(60)

    mock_repo = AsyncMock()
    mock_repo.get_by_ticker.return_value = _make_swiss_stock("NESN")

    mock_pred_svc = AsyncMock()
    mock_pred_svc.predict.side_effect = FileNotFoundError("kein Modell")

    from backend.application.services.ml_feature_service import MLFeatureService
    from backend.application.services.ml_prediction_service import MLPredictionService

    real_feature_svc = MLFeatureService(yfinance_adapter=mock_adapter)
    real_pred_svc = MLPredictionService(feature_service=real_feature_svc)

    with patch.object(real_pred_svc, "predict", side_effect=FileNotFoundError("kein Modell")):
        service = SignalAggregationService(
            feature_service=real_feature_svc,
            prediction_service=real_pred_svc,
            swiss_stock_repo=mock_repo,
        )
        result = await service.get_signal("NESN")

    assert result is not None, "SignalAggregationService muss ein Signal zurückgeben"
    assert result.ticker == "NESN"
    assert result.signal in {"BUY", "HOLD", "WATCH"}
    assert 0.0 <= result.confidence <= 1.0
    assert result.ml_score == 50.0  # Fallback weil kein Modell
    # adapter wurde mit korrektem Methodennamen und Argzahl aufgerufen
    mock_adapter.get_fundamentals.assert_awaited_once_with("NESN")
    mock_adapter.get_price_history.assert_awaited_once_with("NESN", days=400)


@pytest.mark.asyncio
async def test_signal_pipeline_get_signals_returns_list() -> None:
    """get_signals für mehrere Ticker: fehlgeschlagene werden übersprungen."""
    mock_adapter = AsyncMock()
    mock_adapter.get_fundamentals.return_value = _make_fundamentals()
    mock_adapter.get_price_history.return_value = _make_price_df(60)
    mock_repo = AsyncMock()
    mock_repo.get_by_ticker.return_value = _make_swiss_stock()

    from backend.application.services.ml_feature_service import MLFeatureService
    from backend.application.services.ml_prediction_service import MLPredictionService

    real_feature_svc = MLFeatureService(yfinance_adapter=mock_adapter)

    with patch.object(MLPredictionService, "predict", side_effect=FileNotFoundError):
        service = SignalAggregationService(
            feature_service=real_feature_svc,
            swiss_stock_repo=mock_repo,
        )
        results = await service.get_signals(["NESN", "NOVN"])

    assert len(results) == 2
    assert all(isinstance(r, DecisionSignal) for r in results)


@pytest.mark.asyncio
async def test_signal_pipeline_no_market_data_returns_none() -> None:
    """Fehlende Marktdaten → None (kein Crash)."""
    mock_adapter = AsyncMock()
    mock_adapter.get_fundamentals.side_effect = Exception("yfinance timeout")

    from backend.application.services.ml_feature_service import MLFeatureService

    real_feature_svc = MLFeatureService(yfinance_adapter=mock_adapter)
    service = SignalAggregationService(feature_service=real_feature_svc)
    result = await service.get_signal("UNKNOWN")
    assert result is None


# ---------------------------------------------------------------------------
# MacroService — Markdown-Stripping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_macro_service_strips_markdown_json() -> None:
    """Prüft Bug: LLM gibt ```json...``` zurück → muss trotzdem geparst werden."""
    markdown_response = '```json\n{"de": "SNB senkt Zins. Positiv für Aktien.", "en": "SNB cuts rate. Positive for stocks."}\n```'

    llm = AsyncMock()
    llm_resp = MagicMock()
    llm_resp.content = [MagicMock(text=markdown_response)]
    llm.messages_create.return_value = llm_resp

    with (
        patch("backend.application.services.macro_service.fetch_current_snb_rate", new=AsyncMock(return_value=0.0)),
        patch("backend.application.services.macro_service._fetch_chf_eur", return_value=0.931),
    ):
        service = MacroService(llm_client=llm)
        ctx = await service.get_context()

    # Ohne Markdown-Stripping wäre dies der Fallback-Text gewesen
    assert ctx.narrative_de == "SNB senkt Zins. Positiv für Aktien."
    assert ctx.narrative_en == "SNB cuts rate. Positive for stocks."
    assert isinstance(ctx, MacroContext)


@pytest.mark.asyncio
async def test_macro_service_strips_plain_backtick_block() -> None:
    """Auch ```...``` ohne 'json'-Label wird korrekt gestripped."""
    plain_block = '```\n{"de": "Stabiles Umfeld für CHF-Investoren.", "en": "Stable environment for CHF investors."}\n```'

    llm = AsyncMock()
    llm_resp = MagicMock()
    llm_resp.content = [MagicMock(text=plain_block)]
    llm.messages_create.return_value = llm_resp

    with (
        patch("backend.application.services.macro_service.fetch_current_snb_rate", new=AsyncMock(return_value=0.25)),
        patch("backend.application.services.macro_service._fetch_chf_eur", return_value=0.93),
    ):
        service = MacroService(llm_client=llm)
        ctx = await service.get_context()

    assert ctx.narrative_de == "Stabiles Umfeld für CHF-Investoren."


@pytest.mark.asyncio
async def test_macro_service_handles_trailing_whitespace() -> None:
    """LLM gibt JSON mit führenden/trailing Whitespace zurück — kein Crash."""
    padded = '  \n{"de": "Leitzins unverändert. Neutrales Klima.", "en": "Rate unchanged. Neutral climate."}\n  '

    llm = AsyncMock()
    llm_resp = MagicMock()
    llm_resp.content = [MagicMock(text=padded)]
    llm.messages_create.return_value = llm_resp

    with (
        patch("backend.application.services.macro_service.fetch_current_snb_rate", new=AsyncMock(return_value=0.5)),
        patch("backend.application.services.macro_service._fetch_chf_eur", return_value=0.92),
    ):
        service = MacroService(llm_client=llm)
        ctx = await service.get_context()

    assert "Leitzins" in ctx.narrative_de


# ---------------------------------------------------------------------------
# PortfolioAgent — Markdown-Stripping in Narrative
# ---------------------------------------------------------------------------


def _mock_rankings(tickers: list[str]) -> list[dict]:
    return [
        {"ticker": t, "total_rank": i + 1, "weighted_avg": 80.0 - i * 5}
        for i, t in enumerate(tickers)
    ]


@pytest.mark.asyncio
async def test_portfolio_agent_strips_markdown_json_narrative() -> None:
    """Prüft Bug: LLM-Narrative als ```json...``` → muss trotzdem geparst werden."""
    tickers = ["NESN", "NOVN"]
    markdown_narrative = (
        '```json\n'
        '{"overall": "Defensives Portfolio mit zwei Schweizer Blue Chips.",'
        ' "positions": {"NESN": "Nahrungsmittelriese, stabile Dividende.", "NOVN": "Pharma-Exposure."}}'
        '\n```'
    )

    run_svc = AsyncMock()
    run_svc.get_rankings.return_value = _mock_rankings(tickers)
    repo = AsyncMock()
    repo.get_by_ticker.return_value = _make_swiss_stock("NESN")

    llm = AsyncMock()
    llm_resp = MagicMock()
    llm_resp.content = [MagicMock(text=markdown_narrative)]
    llm.messages_create.return_value = llm_resp

    agent = PortfolioAgent(
        ranking_run_service=run_svc,
        swiss_stock_repo=repo,
        llm_client=llm,
    )
    result = await agent.allocate(run_id=uuid4(), top_n=2)

    assert "Defensives Portfolio" in result.overall_rationale_de
    # Rationale muss aus LLM kommen, nicht Fallback
    assert any("Nahrungsmittelriese" in p.rationale_de for p in result.positions)


@pytest.mark.asyncio
async def test_portfolio_agent_json_serializable_allocation() -> None:
    """PortfolioAllocation muss JSON-serialisierbar sein (für REST-Response).

    Prüft Bug: UUID/datetime/Decimal in Dataclass sind nicht default-json-serialisierbar.
    """
    import json as stdlib_json

    run_svc = AsyncMock()
    run_svc.get_rankings.return_value = _mock_rankings(["NESN", "NOVN", "ROG"])
    repo = AsyncMock()
    repo.get_by_ticker.return_value = _make_swiss_stock("NESN")

    agent = PortfolioAgent(
        ranking_run_service=run_svc,
        swiss_stock_repo=repo,
        llm_client=None,
    )
    result = await agent.allocate(run_id=uuid4(), top_n=3)

    # Simuliert REST-Serialisierung (FastAPI macht dasselbe intern)
    payload = {
        "run_id": str(result.run_id),
        "method": result.method,
        "positions": [
            {
                "ticker": p.ticker,
                "weight": p.weight,
                "quant_score": p.quant_score,
                "is_3a_eligible": p.is_3a_eligible,
                "rationale_de": p.rationale_de,
            }
            for p in result.positions
        ],
        "overall_rationale_de": result.overall_rationale_de,
        "computed_at": result.computed_at.isoformat(),
        "eligible_only": result.eligible_only,
        "total_positions": len(result.positions),
    }
    # Darf nicht werfen
    stdlib_json.dumps(payload)
    assert len(result.positions) == 3
    assert abs(sum(p.weight for p in result.positions) - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_portfolio_agent_messages_create_called_with_correct_kwargs() -> None:
    """Prüft Arg-Anzahl + Kwarg-Namen des LLM-Calls im PortfolioAgent.

    Fängt: positionale statt keyword-Argumente, fehlendes 'feature'-Tag.
    """
    run_svc = AsyncMock()
    run_svc.get_rankings.return_value = _mock_rankings(["NESN"])
    repo = AsyncMock()
    repo.get_by_ticker.return_value = _make_swiss_stock("NESN")

    llm = AsyncMock()
    llm_resp = MagicMock()
    llm_resp.content = [MagicMock(text='{"overall": "Einzel-Position.", "positions": {"NESN": "Marktführer."}}')]
    llm.messages_create.return_value = llm_resp

    agent = PortfolioAgent(
        ranking_run_service=run_svc,
        swiss_stock_repo=repo,
        llm_client=llm,
    )
    await agent.allocate(run_id=uuid4(), top_n=1)

    call_kwargs = llm.messages_create.call_args.kwargs
    assert "model" in call_kwargs
    assert "messages" in call_kwargs
    assert "max_tokens" in call_kwargs
    assert "feature" in call_kwargs
    assert call_kwargs["feature"] == "portfolio_narrative"
    assert isinstance(call_kwargs["messages"], list)
    assert call_kwargs["messages"][0]["role"] == "user"


# ---------------------------------------------------------------------------
# SteuerAgent — Markdown-Stripping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steuer_agent_strips_markdown_json() -> None:
    """Prüft Bug: SteuerAgent ohne .strip() schluckt trailing newline nicht."""
    from backend.application.agents.steuer_agent import SteuerAgent
    from backend.domain.schemas.steuer_schema import PFLICHT_DISCLAIMER

    valid_output = {
        "steuerarten": ["Verrechnungssteuer (35%)"],
        "pflichten": ["VST-Rückerstattung via Formular 103"],
        "hinweise": ["Steuerbefreiung bei 3a gilt laufend"],
        "quellen": ["ESTV"],
        "disclaimer": PFLICHT_DISCLAIMER,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": "claude-sonnet-4-6",
    }
    # Markdown-umwickeltes JSON mit trailing newline — der originale Bug
    markdown_text = f"```json\n{json.dumps(valid_output)}\n```\n"

    mock_retrieval = AsyncMock()
    mock_retrieval.retrieve.return_value = []
    mock_content = MagicMock()
    mock_content.text = markdown_text
    mock_llm = AsyncMock()
    mock_llm.messages_create.return_value = MagicMock(content=[mock_content])
    mock_prompts = MagicMock()
    mock_prompts.render.return_value = "rendered"

    agent = SteuerAgent(
        llm_client=mock_llm,
        retrieval_service=mock_retrieval,
        prompt_loader=mock_prompts,
    )
    result = await agent.einschaetzen("NESN", "vorsorge_3a", 30)

    assert result.ticker == "NESN"
    assert result.model_version != "fallback", "Markdown-Stripping hat versagt — Fallback aktiv"
    assert result.disclaimer == PFLICHT_DISCLAIMER
