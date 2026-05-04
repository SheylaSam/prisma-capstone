"""NarrativeService — orchestriert Memo-Generation Ende-zu-Ende.

Spec: docs/specs/2026-05-04-narrative-engine-single-memo.md.

In dieser Datei (alles Service-internes Detail):
- `UniverseContext` (Pydantic-Value-Object — nur 1 Consumer im MVP)
- `_extract_ranking_for_ticker` (Helper)
- `_build_universe_context` (Helper)
- `NarrativeService` (Klasse mit get_memo + generate_memo)
"""

from __future__ import annotations

from statistics import median
from typing import Any

from pydantic import BaseModel, Field


class UniverseContext(BaseModel):
    """Aggregierte Verteilungs-Metadaten fuer den User-Prompt.

    Wird im Service aus dict-list-Results von RankingRunRepository abgeleitet.
    Keine eigene Datei (YAGNI — nur 1 Consumer).
    """

    model_config = {"frozen": True}

    n_stocks: int = Field(..., ge=1)
    median_rank: int = Field(..., ge=1)
    top20_threshold: int = Field(..., ge=1)


def _extract_ranking_for_ticker(
    results: list[dict[str, Any]], *, ticker: str
) -> dict[str, Any]:
    """Filtert den Ranking-Eintrag fuer einen bestimmten Ticker.

    Wirft KeyError, wenn der Ticker nicht im Run vorkommt.
    """
    for row in results:
        if row["ticker"] == ticker:
            return row
    raise KeyError(f"Ticker {ticker} not in run results")


def _build_universe_context(results: list[dict[str, Any]]) -> UniverseContext:
    """Berechnet aggregierte Stats (n, median, top20-threshold) aus dict-list."""
    ranks = sorted(int(r["total_rank"]) for r in results if r.get("total_rank") is not None)
    if not ranks:
        raise ValueError("Keine validen total_ranks in den Results")

    n = len(ranks)
    median_rank = int(median(ranks))
    # 20%-Perzentile via Index-Lookup; fuer kleine N robust ohne numpy
    idx = max(0, int(round(0.20 * (n - 1))))
    top20_threshold = ranks[idx]

    return UniverseContext(
        n_stocks=n, median_rank=median_rank, top20_threshold=top20_threshold
    )


class NarrativeService:
    """Memo-Generation. Implementation kommt in Tasks 6-8."""

    def __init__(self) -> None:
        raise NotImplementedError("NarrativeService wird in Task 6 vollstaendig implementiert")
