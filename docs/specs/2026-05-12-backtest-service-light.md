# Spec: BacktestService — Light (MVP-Slice)

**Status**: Draft v1.0 — 2026-05-12
**Rolle**: A — Quant Core (Fabia)
**Parent-Spec**: `docs/specs/2026-04-21-prisma-capstone-design.md` §7.4 + §9.5
**Spec-Konvention**: AGENTS.md §3 "Wenn ein neues Quant-Modell/Service implementiert wird"

---

## 1. Zweck

Implementiert die Light-Variante des `BacktestService` aus Design-Spec §7.4. Erlaubt einem User, einen abgeschlossenen `ModelRun` als Startpunkt zu nehmen und das resultierende Top-N-Portfolio über einen Zeitraum gegen zwei Benchmarks zu vergleichen. Liefert annualisierte Rendite, annualisierte Volatilität, Sharpe-Ratio und Maximum Drawdown.

**Slicing-Begründung:** Die "echte" Backtest-Variante mit monatlichem Re-Ranking (RankingService N-mal über die History laufen lassen) ist 5-10× komplexer und braucht ein Snapshot-Konzept für Universe + Prices zu jedem Rebalancing-Datum. Die Light-Variante validiert Entity, Repository, REST-Endpoints, Metriken-Berechnung und Frontend-Anbindung Ende-zu-Ende und ist damit auch das Capstone-Demo-Asset (Spec §14.3 Z. 649: "Backtest starten → Chart mit 3 Kurven").

---

## 2. Scope

### In Scope

- `BacktestService.run_backtest(universe_id, model_run_id, start_date, end_date, top_n)` und `.get_backtest_result(id)`
- `BacktestResult`-Entity + ORM + Alembic-Migration
- `BacktestResultRepository` (Port + SQLA-Adapter)
- 3 simulierte Portfolios, alle gleichgewichtet, monatlich rebalanciert (Reset auf Equal-Weight):
  | Portfolio | Beschreibung |
  |---|---|
  | PRISMA Top-N | Top-N aus dem übergebenen ModelRun, EW |
  | Equal-Weight Universe | Alle Ticker im Universe, EW |
  | Benchmark | `^SSMI` (Default, konfigurierbar via Request) — über `MarketDataProvider` |
- Metriken (alle annualisiert): Total Return, CAGR, Volatilität, Sharpe (rf=0), Max Drawdown
- 2 REST-Endpoints: `POST /api/v1/backtests/run`, `GET /api/v1/backtests/{id}`
- Pydantic-Request/Response-Schemas
- Test-Stack: Unit (Service-Logik + Metriken), Integration (REST + Repository), Golden-Dataset

### Out of Scope (Folge-Slices)

- **Monatliches Re-Ranking**: RankingService bei jedem Rebalancing-Datum neu auf History laufen lassen. Erfordert eigenes Spec-Slice mit Snapshot-Konzept.
- **Walk-Forward-Analyse** (Design-Spec §17 Backlog Z. 799)
- **Transaktionskosten-Modell** (Design-Spec §17 Backlog Z. 800)
- **Universe-Drift während Backtest-Periode**
- **Asynchroner Run** (Light-Variante: sync, ggf. <30s — Universe ≤50 Ticker, 5J-Window)
- **Backtest-zu-Backtest-Vergleich** (mehrere Runs in einer UI-View)

---

## 3. Architektur

### Dateistruktur

```
backend/
├── application/services/
│   └── backtest_service.py                # NEU
├── domain/
│   ├── entities/
│   │   └── backtest_result.py             # NEU
│   └── repositories/
│       └── backtest_result_repository.py  # NEU (Port)
├── infrastructure/persistence/
│   ├── models/
│   │   └── backtest_result.py             # NEU (ORM)
│   ├── repositories/
│   │   └── backtest_result_repository.py  # NEU (SQLA-Adapter)
│   └── alembic/versions/
│       └── 0007_create_backtest_results.py # NEU
└── interfaces/rest/
    ├── routers/backtests.py               # NEU
    └── dependencies.py                    # ERWEITERT (Repository + Service)
```

### Komponenten-Verantwortung

| Komponente | Verantwortung | Tests |
|---|---|---|
| `BacktestService` | Orchestriert: Top-N aus ModelRun laden → Preise via MarketDataProvider → 3 Portfolios simulieren → Metriken berechnen → Persistieren. | Unit (Service mit Mock-Repos) + Integration (PG) |
| `BacktestResult` | Pydantic-Entity mit `metrics: dict`, `series: dict[str, list[float]]`, dates, top_n, universe_id, model_run_id. | Unit |
| `BacktestResultRepository` | Domain-Port + SQLA-Adapter (`save`, `get`). UPSERT auf `(universe_id, model_run_id, start_date, end_date, top_n)` falls Re-Run gewünscht. | Integration (PG) |
| `backtests.py`-Router | REST-Endpoints, FastAPI-DI, Pydantic-Request/Response. | Integration (FastAPI TestClient) |

---

## 4. Data Flow

```
POST /api/v1/backtests/run
{ universe_id, model_run_id, start_date, end_date, top_n=10, benchmark_ticker="^SSMI" }
  │
  ▼
BacktestService.run_backtest(...)
  │
  ├─ 1. Validate inputs:
  │     - universe_id, model_run_id existieren (404 falls nein)
  │     - start_date < end_date, beide ≤ today
  │     - top_n > 0, top_n ≤ universe.stock_count
  │     - end_date - start_date ≥ 30 Tage (sonst Metriken unzuverlässig)
  │
  ├─ 2. Top-N-Tickers laden:
  │     run_repo.get_total_ranks(model_run_id)
  │     → Sortieren nach total_rank, ersten top_n nehmen
  │
  ├─ 3. Universe-Tickers laden + Benchmark-Ticker hinzufügen:
  │     all_tickers = universe.tickers ∪ {benchmark_ticker}
  │
  ├─ 4. Prices fetch (parallel):
  │     market_data.get_prices_range(all_tickers, start_date, end_date)
  │     → DataFrame mit DatetimeIndex (Trading-Days) und Ticker-Spalten
  │     → 404 wenn weniger Trading-Days als 20 vorhanden
  │
  ├─ 5. 3 Portfolios simulieren (siehe §5):
  │     prisma_series   = _simulate_portfolio(prices[top_n_tickers], rebalance="monthly")
  │     universe_series = _simulate_portfolio(prices[universe.tickers], rebalance="monthly")
  │     benchmark_series = prices[benchmark_ticker] / prices[benchmark_ticker].iloc[0]
  │
  ├─ 6. Metriken berechnen je Portfolio (siehe §6)
  │
  ├─ 7. Persist:
  │     result = BacktestResult(
  │         id=uuid4(), universe_id, model_run_id, start_date, end_date, top_n,
  │         benchmark_ticker,
  │         metrics={
  │             "prisma":    {...},
  │             "universe":  {...},
  │             "benchmark": {...}
  │         },
  │         series={
  │             "dates":     [iso-strings],
  │             "prisma":    [floats],
  │             "universe":  [floats],
  │             "benchmark": [floats]
  │         },
  │         created_at=now(UTC),
  │     )
  │     await backtest_repo.save(result)
  │
  └─ return result
```

---

## 5. Portfolio-Simulation

### `_simulate_portfolio(prices: pd.DataFrame, rebalance: Literal["monthly"]) -> pd.Series`

Equal-Weight-Portfolio mit periodischem Reset-auf-Equal-Weight:

```python
# Pseudocode
returns = prices.pct_change().fillna(0)  # Tagesrenditen pro Ticker
n = len(prices.columns)
weights = np.full(n, 1/n)  # Start: 1/N pro Ticker
portfolio_returns = []
rebalance_dates = _monthly_rebalance_dates(prices.index)

for date in prices.index:
    daily_return = (weights * returns.loc[date]).sum()
    portfolio_returns.append(daily_return)
    # Update weights nach Tagesrendite (Drift)
    weights = weights * (1 + returns.loc[date])
    weights = weights / weights.sum()  # Re-normalisieren auf 100%
    # Monatliches Rebalancing: Reset auf Equal-Weight
    if date in rebalance_dates:
        weights = np.full(n, 1/n)

return (1 + pd.Series(portfolio_returns, index=prices.index)).cumprod()
```

**Edge-Cases:**
- Ticker mit NaN-Returns am Anfang (late listing) → in `prices.pct_change()` als NaN → `fillna(0)` setzt auf 0. **Bewusst**: alternative wäre den Ticker temporär aus weights zu entfernen, aber das verkompliziert ohne MVP-Nutzen.
- Ticker mit Konkurs / Delisting in der History → letzter verfügbarer Preis wird forward-gefüllt (`prices.ffill()` vor `pct_change()`). Ist Approximation, OK für MVP.
- Weniger als 1 voller Monat zwischen start_date und end_date → kein Rebalancing, Reine Drift.

---

## 6. Metriken

Für jede Portfolio-Reihe `series: pd.Series` (kumulierte Werte beginnend bei 1.0):

```python
def _compute_metrics(series: pd.Series) -> dict[str, float]:
    n_days = len(series)
    years = n_days / 252.0

    total_return = series.iloc[-1] / series.iloc[0] - 1.0
    cagr = (series.iloc[-1] / series.iloc[0]) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    daily_returns = series.pct_change().dropna()
    annual_vol = daily_returns.std() * np.sqrt(252)
    sharpe = (cagr / annual_vol) if annual_vol > 0 else 0.0  # rf=0

    cummax = series.cummax()
    drawdown = (series - cummax) / cummax
    max_drawdown = float(drawdown.min())

    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "annual_vol": float(annual_vol),
        "sharpe": float(sharpe),
        "max_drawdown": max_drawdown,
    }
```

**Konventionen:**
- `rf=0` für Sharpe (vereinfachend; Spec §17 Z. 776 erlaubt Default-Annahmen)
- `252` Trading-Days/Jahr (konsistent mit Diversification-Spec)
- Negative CAGR-Werte sind erlaubt (Bear Markets)
- `sharpe` ohne Vol-Schutz: wenn Vol=0, Sharpe=0 (statt division by zero)

---

## 7. REST-Endpoints

### `POST /api/v1/backtests/run`

```jsonc
// Request
{
  "universe_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_run_id": "550e8400-e29b-41d4-a716-446655440001",
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "top_n": 10,
  "benchmark_ticker": "^SSMI"  // optional, default "^SSMI"
}

// 200 Response (kompletter BacktestResult, siehe §4 Schritt 7)
```

**Status-Codes:**
- `200`: Backtest erfolgreich
- `400`: Validierungs-Fehler (z.B. start_date ≥ end_date, top_n > universe.size)
- `404`: Universe oder ModelRun nicht gefunden
- `422`: Pydantic-Schema-Fehler
- `503`: MarketDataProvider liefert keine Preise für den Zeitraum

### `GET /api/v1/backtests/{id}`

- `200`: Backtest-Result existiert
- `404`: nicht gefunden

---

## 8. Entity + Pydantic-Schemas

```python
# backend/domain/entities/backtest_result.py
class BacktestResult(BaseModel):
    id: UUID
    universe_id: UUID
    model_run_id: UUID
    start_date: date
    end_date: date
    top_n: int = Field(..., ge=1, le=100)
    benchmark_ticker: str = Field(..., max_length=20)
    metrics: dict[str, dict[str, float]]  # {"prisma": {...}, "universe": {...}, "benchmark": {...}}
    series: dict[str, list]  # {"dates": [...], "prisma": [...], "universe": [...], "benchmark": [...]}
    created_at: datetime
```

**Validierung:**
- `series["dates"]`, `series["prisma"]`, `series["universe"]`, `series["benchmark"]` müssen gleich lang sein
- Alle floats ≥ 0 in den Series (Portfolio-Wert kann nicht negativ werden)
- `top_n` ≤ 100 (Sanity-Cap)

---

## 9. Test-Strategie

### 9.1 Unit-Tests (`backend/tests/unit/`)

| Datei | Was getestet wird |
|---|---|
| `test_backtest_service.py` | 5 Pfade mit Mock-Repos: (1) Happy-Path mit 5-Ticker-Universe + Top-3, deterministische Preise; (2) Top-N > universe.size → 400; (3) start_date ≥ end_date → 400; (4) Universe nicht gefunden → 404; (5) MarketDataProvider liefert leeren DataFrame → 503 |
| `test_backtest_metrics.py` | Golden-Dataset für `_compute_metrics`: konstante 10% Jahres-Performance → CAGR≈0.10, Vol≈0, Sharpe=0, MaxDD=0. Eine 50%-Drawdown-Reihe → MaxDD≈-0.50 |
| `test_backtest_portfolio_simulation.py` | `_simulate_portfolio` deterministisch: 2 Ticker × 2 Monate, Reset auf 50/50 nach Monatsende verifizieren |
| `test_backtest_result_entity.py` | Pydantic-Validation: ungleiche Series-Längen → ValidationError, top_n > 100 → ValidationError |

### 9.2 Integration-Tests (`backend/tests/integration/`)

| Datei | Was getestet wird |
|---|---|
| `test_backtest_service_integration.py` | Echte PG (Testcontainers) + Stub-MarketDataProvider mit kalibrierten Preisen. End-to-End: POST → DB → GET → Response-Shape |
| `test_backtests_endpoint.py` | FastAPI TestClient: POST happy, POST 400 (invalid), GET 200, GET 404 |

### 9.3 Golden-Dataset

`backend/tests/fixtures/backtest/perfect_strategy.json`:
- 5 Ticker × 36 Monate
- PRISMA Top-3 sind die mit der niedrigsten Vola
- Erwartete Metriken vorab berechnet (numpy in Spec-Generierung verifiziert)
- Test prüft Metrik-Übereinstimmung mit ±0.1%-Toleranz

### 9.4 Coverage-Ziel

- Unit: ≥90% (Service + Helpers)
- Integration: ≥80%
- Gesamtsuite: bleibt ≥80% per `fail_under` (PR #83)

---

## 10. Akzeptanz-Kriterien

Implementation ist komplett, wenn:

- [ ] `BacktestResult`-Entity (Pydantic v2, UTC-aware) in `backend/domain/entities/`
- [ ] `BacktestResultRepository`-Port + SQLA-Adapter mit UPSERT-Logik
- [ ] Alembic-Migration `0007_create_backtest_results` (reversibel)
- [ ] `BacktestService` mit `run_backtest` und `get_backtest_result` (siehe §3)
- [ ] `_simulate_portfolio` mit monatlichem Reset-Rebalancing (siehe §5)
- [ ] `_compute_metrics` mit allen 5 Metriken (siehe §6)
- [ ] `POST /api/v1/backtests/run` und `GET /api/v1/backtests/{id}` live, in OpenAPI-Schema sichtbar
- [ ] Alle Tests aus §9.1 und §9.2 grün
- [ ] Golden-Dataset-Metriken matchen Spec-Erwartungen (±0.1%)
- [ ] Coverage neue Module ≥85%; Gesamtsuite bleibt ≥80% (CI-Gate aus PR #83)
- [ ] mypy strict + ruff clean
- [ ] Sample-Backtest-Result unter `docs/examples/backtest-result-sample.json`
- [ ] AI-USAGE.md-Eintrag (40%-Achse Capstone)
- [ ] README-Sektion "Backtest" mit Kurz-Anleitung (Curl-Example)

---

## 11. Bewusste Abweichungen von Parent-Spec

| Parent-Spec-Stelle | Slice-Verhalten | Begründung |
|---|---|---|
| §7.4 — "monatliches Rebalancing **nach Total Rank**" | Rebalancing = Reset auf Equal-Weight (kein neues Ranking) | "Echtes" Re-Ranking braucht Historical-Snapshot-Konzept (Universe + Prices zu jedem Datum) — eigener Folge-Slice. Equal-Weight-Reset ist die naive aber spec-getreue Light-Interpretation. |
| §9.5 — `run_backtest` Input nur `(Universe-ID, Start/End, Top-N)` | Zusätzlich `model_run_id` und `benchmark_ticker` als Inputs | Ohne `model_run_id` müsste BacktestService einen impliziten "neuesten" Run wählen oder selbst einen neuen erzeugen. Explizit ist klarer. `benchmark_ticker` als Default `^SSMI` + Konfig-Override. |
| §10.1 — Endpoint-Path | `/api/v1/backtests/run` und `/api/v1/backtests/{id}` | Konsistent mit den anderen Service-Pfaden (`/api/v1/...`). |
| §14.3 — "Chart mit 3 Kurven" | 3 Portfolios: PRISMA Top-N + Universe-EW + Benchmark | Spec lässt offen welche 3. Diese Wahl bildet die "lohnt sich der Ranking-Aufwand?"-Frage (vs. Universe-EW als Naivität, vs. Benchmark als Markt-Baseline) am sinnvollsten ab. |

---

## 12. Offene Punkte vor Plan-Schreiben

1. **Sync vs. Async**: MVP-Light ist sync (5J-Backtest mit Stub-Daten <2s). Bei echtem yfinance-Adapter wird Backtest >10s → async via Job-Queue nötig. Folge-Slice.
2. **Universe-Drift**: aktueller Slice ignoriert, dass ein Universe im Lauf der Zeit hinzugefügte/entfernte Ticker hat. Implementation nutzt das *aktuelle* Universe für die ganze Backtest-Periode. Akzeptabel für Light-Variante.
3. **Benchmark-Datenquelle**: `^SSMI` kommt über den gleichen `MarketDataProvider` — Stub liefert für unbekannte Ticker einen 100-Random-Walk. Für die echte Demo brauchts ggf. einen separaten Index-Adapter. Folge-Slice.

---

## 13. Änderungshistorie

| Version | Datum | Autor | Änderung |
|---|---|---|---|
| Draft v1.0 | 2026-05-12 | Fabia / Claude Code Opus 4.7 | Initiale Slice-Spec — BacktestService Light, schneidet Monthly-Re-Ranking und Walk-Forward bewusst heraus |
