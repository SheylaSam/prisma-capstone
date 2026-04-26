"""CostTracker — Application-Service für Cap-Checks und Cost-Recording.

Spezifiziert in `docs/specs/2026-04-25-budget-cap.md` §5.

Wird vom `LLMClient`-Wrapper in der Infrastructure-Schicht aufgerufen:
- `check_cap(estimated_usd)` vor jedem LLM-Call: wirft `BudgetCapExceeded`,
  wenn das Monats-Budget um die Schätzung überschritten würde
- `record(...)` nach jedem erfolgreichen Call: berechnet Kosten aus Tokens
  und schreibt eine Audit-Zeile in `llm_call_log`

Concurrency: ein kleines Race-Window existiert (zwei parallele Calls passen
beide `check_cap` und schreiben dann beide `record`). Bei Capstone-Volumen
(max ~30 Calls/Batch) absorbiert die 5%-Schwelle das. Anthropic-Console
Spend-Limit ist Backstop.
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.errors import BudgetCapExceeded
from backend.infrastructure.llm.pricing import PRICING
from backend.infrastructure.persistence.models.llm_call_log import LLMCallLogORM


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
