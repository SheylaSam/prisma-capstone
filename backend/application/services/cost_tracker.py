"""CostTracker — Application-Service für Cap-Checks, Cost-Recording und Summary.

Spezifiziert in `docs/specs/2026-04-25-budget-cap.md` §5 + §9.

Wird vom `LLMClient`-Wrapper in der Infrastructure-Schicht aufgerufen:
- `check_cap(estimated_usd)` vor jedem LLM-Call: wirft `BudgetCapExceeded`,
  wenn das Monats-Budget um die Schätzung überschritten würde
- `record(...)` nach jedem erfolgreichen Call: berechnet Kosten aus Tokens
  und schreibt eine Audit-Zeile in `llm_call_log`
- `summary(last_n)` liefert aggregierte Kosten-Übersicht für den Admin-Endpoint

Concurrency: ein kleines Race-Window existiert (zwei parallele Calls passen
beide `check_cap` und schreiben dann beide `record`). Bei Capstone-Volumen
(max ~30 Calls/Batch) absorbiert die 5%-Schwelle das. Anthropic-Console
Spend-Limit ist Backstop.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.errors import BudgetCapExceeded
from backend.infrastructure.llm.pricing import PRICING
from backend.infrastructure.persistence.models.llm_call_log import LLMCallLogORM


# ---------------------------------------------------------------------------
# Dataclasses für CostSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelBreakdown:
    model: str
    calls: int
    cost_usd: Decimal


@dataclass(frozen=True)
class FeatureBreakdown:
    feature: str
    calls: int
    cost_usd: Decimal


@dataclass(frozen=True)
class CallEntry:
    created_at: datetime
    model: str
    feature: str
    cost_usd: Decimal


@dataclass(frozen=True)
class CostSummary:
    month: str  # "YYYY-MM"
    cap_usd: Decimal
    current_usd: Decimal
    remaining_usd: Decimal  # max(cap - current, 0)
    by_model: list[ModelBreakdown]
    by_feature: list[FeatureBreakdown]
    last_calls: list[CallEntry]


# ---------------------------------------------------------------------------
# SQL-Queries (module-level Konstanten)
# ---------------------------------------------------------------------------

# SQL-Query für Monatskosten (Kalender-Monat UTC, synchron mit Anthropic
# Console Spend-Limit). Kein ORM-Layer für diesen Performance-kritischen Pfad.
_CURRENT_MONTH_SUM_SQL = text(
    """
    SELECT COALESCE(SUM(cost_usd), 0)
    FROM llm_call_log
    WHERE created_at >= date_trunc('month', now() AT TIME ZONE 'UTC')
      AND created_at <  date_trunc('month', now() AT TIME ZONE 'UTC')
                         + INTERVAL '1 month'
    """
)

_BY_MODEL_SQL = text(
    """
    SELECT model, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd
    FROM llm_call_log
    WHERE created_at >= date_trunc('month', now() AT TIME ZONE 'UTC')
      AND created_at <  date_trunc('month', now() AT TIME ZONE 'UTC')
                         + INTERVAL '1 month'
    GROUP BY model
    ORDER BY cost_usd DESC
    """
)

_BY_FEATURE_SQL = text(
    """
    SELECT feature, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd
    FROM llm_call_log
    WHERE created_at >= date_trunc('month', now() AT TIME ZONE 'UTC')
      AND created_at <  date_trunc('month', now() AT TIME ZONE 'UTC')
                         + INTERVAL '1 month'
    GROUP BY feature
    ORDER BY cost_usd DESC
    """
)

_LAST_CALLS_SQL = text(
    """
    SELECT created_at, model, feature, cost_usd
    FROM llm_call_log
    WHERE created_at >= date_trunc('month', now() AT TIME ZONE 'UTC')
      AND created_at <  date_trunc('month', now() AT TIME ZONE 'UTC')
                         + INTERVAL '1 month'
    ORDER BY created_at DESC
    LIMIT :limit
    """
)


class CostTracker:
    def __init__(
        self,
        *,
        session: AsyncSession,
        cap_usd: Decimal,
        threshold: Decimal = Decimal("0.95"),
    ) -> None:
        self._session = session
        self._cap_usd = cap_usd
        self._threshold = threshold

    async def _current_month_usd(self) -> Decimal:
        """SUM(cost_usd) für den aktuellen Kalender-Monat UTC.

        Wird von Tests via Monkey-Patch ersetzt — Boundary-Logik ist damit
        ohne echte DB testbar.
        """
        result = await self._session.execute(_CURRENT_MONTH_SUM_SQL)
        # COALESCE garantiert nicht-NULL; Driver liefert Decimal oder int
        raw = result.scalar_one()
        return Decimal(str(raw))

    async def check_cap(self, *, estimated_usd: Decimal) -> None:
        """Wirft BudgetCapExceeded, wenn (current + estimated) > cap * threshold."""
        current = await self._current_month_usd()
        if (current + estimated_usd) > self._cap_usd * self._threshold:
            raise BudgetCapExceeded(
                current_usd=current,
                attempted_usd=estimated_usd,
                cap_usd=self._cap_usd,
            )

    async def record(
        self,
        *,
        provider: str,
        model: str,
        feature: str,
        input_tokens: int,
        output_tokens: int,
        request_id: str | None = None,
    ) -> None:
        """Berechnet Kosten aus Tokens und persistiert eine Audit-Zeile."""
        cost_usd = self._compute_cost_usd(model, input_tokens, output_tokens)
        entry = LLMCallLogORM(
            provider=provider,
            model=model,
            feature=feature,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            request_id=request_id,
        )
        self._session.add(entry)
        await self._session.commit()

    async def summary(self, *, last_n: int = 10) -> CostSummary:
        """Liefert aggregierte Kosten-Übersicht für den aktuellen Kalender-Monat UTC.

        Drei SQL-Queries: SUM für cap-Status, GROUP BY model, GROUP BY feature,
        LIMIT :limit für letzte Calls. Spezifiziert in §9.
        """
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        current_usd = await self._current_month_usd()
        cap_usd = self._cap_usd
        remaining_usd = max(cap_usd - current_usd, Decimal("0"))

        model_result = await self._session.execute(_BY_MODEL_SQL)
        by_model = sorted(
            [
                ModelBreakdown(
                    model=row.model,
                    calls=row.calls,
                    cost_usd=Decimal(str(row.cost_usd)),
                )
                for row in model_result.fetchall()
            ],
            key=lambda b: b.cost_usd,
            reverse=True,
        )

        feature_result = await self._session.execute(_BY_FEATURE_SQL)
        by_feature = sorted(
            [
                FeatureBreakdown(
                    feature=row.feature,
                    calls=row.calls,
                    cost_usd=Decimal(str(row.cost_usd)),
                )
                for row in feature_result.fetchall()
            ],
            key=lambda b: b.cost_usd,
            reverse=True,
        )

        last_result = await self._session.execute(_LAST_CALLS_SQL, {"limit": last_n})
        last_calls = [
            CallEntry(
                created_at=row.created_at,
                model=row.model,
                feature=row.feature,
                cost_usd=Decimal(str(row.cost_usd)),
            )
            for row in last_result.fetchall()
        ]

        return CostSummary(
            month=month,
            cap_usd=cap_usd,
            current_usd=current_usd,
            remaining_usd=remaining_usd,
            by_model=by_model,
            by_feature=by_feature,
            last_calls=last_calls,
        )

    @staticmethod
    def _compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Token-Counts → Kosten in USD via PRICING-Registry.

        Embedding-Modelle (embed_per_mtok ist gesetzt) verwenden nur
        input_tokens; Chat-Modelle verwenden input + output.
        """
        pricing = PRICING[model]
        million = Decimal("1_000_000")
        if pricing.embed_per_mtok is not None:
            return Decimal(input_tokens) * pricing.embed_per_mtok / million
        return (
            Decimal(input_tokens) * pricing.input_per_mtok / million
            + Decimal(output_tokens) * pricing.output_per_mtok / million
        )
