"""Tests für Diversification — Ledoit-Wolf-Kovarianz, Vola + Korrelation.

Spec: docs/specs/2026-04-28-quant-mvp-models.md §5
      docs/specs/2026-04-21-prisma-capstone-design.md §6.5
"""

import numpy as np
import pandas as pd
import pytest

from backend.domain.models.diversification import DiversificationModel

pytestmark = pytest.mark.unit


def _run(prices: pd.DataFrame) -> dict[str, int | None]:
    """Hilfsfunktion: gibt {ticker: rank} zurück."""
    results = DiversificationModel().run(prices=prices)
    return {r.ticker: r.rank for r in results}


def _make_prices(returns: pd.DataFrame, start: float = 100.0) -> pd.DataFrame:
    """Wandelt eine Returns-DataFrame in eine Preis-DataFrame (kumuliert)."""
    return start * (1 + returns).cumprod()


class TestDiversificationFormula:
    def test_low_vol_low_corr_ranks_first(self) -> None:
        """3-Ticker Golden Dataset: A (low vola, low correlation), B (mid), C (high vola, high correlation).
        A muss Rang 1 erhalten, C Rang 3.
        """
        rng = np.random.default_rng(42)
        n_days = 252
        index = pd.date_range("2024-01-01", periods=n_days, freq="B")

        # A: niedrige Vola, unkorreliert
        a_returns = rng.normal(0.0005, 0.005, n_days)
        # B: mittlere Vola, leicht korreliert mit A
        b_returns = 0.3 * a_returns + rng.normal(0.0005, 0.012, n_days)
        # C: hohe Vola, stark korreliert mit B
        c_returns = 0.9 * b_returns + rng.normal(0.0005, 0.025, n_days)

        returns = pd.DataFrame(
            {"A": a_returns, "B": b_returns, "C": c_returns},
            index=index,
        )
        prices = _make_prices(returns)

        ranks = _run(prices)
        assert ranks["A"] == 1
        assert ranks["C"] == 3

    def test_deterministic(self) -> None:
        rng = np.random.default_rng(7)
        index = pd.date_range("2024-01-01", periods=120, freq="B")
        returns = pd.DataFrame(
            {
                "X": rng.normal(0, 0.01, 120),
                "Y": rng.normal(0, 0.02, 120),
                "Z": rng.normal(0, 0.015, 120),
            },
            index=index,
        )
        prices = _make_prices(returns)
        assert _run(prices) == _run(prices)


class TestDiversificationEdgeCases:
    def test_empty_universe_returns_empty(self) -> None:
        prices = pd.DataFrame()
        assert DiversificationModel().run(prices=prices) == []

    def test_single_ticker_gets_rank_one_with_low_confidence(self) -> None:
        rng = np.random.default_rng(0)
        index = pd.date_range("2024-01-01", periods=60, freq="B")
        prices = _make_prices(pd.DataFrame({"SOLO": rng.normal(0, 0.01, 60)}, index=index))

        results = DiversificationModel().run(prices=prices)
        assert len(results) == 1
        assert results[0].ticker == "SOLO"
        assert results[0].rank == 1
        assert results[0].confidence == "low"

    def test_insufficient_datapoints_yields_no_ranks(self) -> None:
        """< 30 Datenpunkte → Ledoit-Wolf instabil → rank=None für alle."""
        rng = np.random.default_rng(1)
        index = pd.date_range("2024-01-01", periods=20, freq="B")
        returns = pd.DataFrame(
            {"A": rng.normal(0, 0.01, 20), "B": rng.normal(0, 0.02, 20)},
            index=index,
        )
        prices = _make_prices(returns)

        results = DiversificationModel().run(prices=prices)
        assert all(r.rank is None for r in results)
        assert all(r.confidence == "low" for r in results)

    def test_zero_variance_ticker_gets_no_rank(self) -> None:
        """Ticker mit konstanten Preisen → std=0 → rank=None, confidence='low'."""
        rng = np.random.default_rng(3)
        n = 80
        index = pd.date_range("2024-01-01", periods=n, freq="B")
        returns = pd.DataFrame(
            {
                "NORMAL_A": rng.normal(0, 0.01, n),
                "NORMAL_B": rng.normal(0, 0.012, n),
                "FLAT": np.zeros(n),
            },
            index=index,
        )
        prices = _make_prices(returns)

        results = {r.ticker: r for r in DiversificationModel().run(prices=prices)}
        assert results["FLAT"].rank is None
        assert results["FLAT"].confidence == "low"
        assert results["NORMAL_A"].rank is not None
        assert results["NORMAL_B"].rank is not None
