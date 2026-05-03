# AI-Usage Log

Reflexions-Tagebuch über den Einsatz von Coding-Agents (Claude Code, Cursor, Copilot, Codex) in diesem Projekt. **Direkt notenrelevant für die 40%-Achse** des Capstone-Bewertungsrasters.

## Format

Pro PR mit substantieller Agent-Beteiligung ein Eintrag:

```markdown
## YYYY-MM-DD · <PR-Titel> (#<PR-Nummer>)
- **Agent**: Claude Code / Cursor / Copilot / Codex
- **Scope**: <1 Satz, was der Agent gemacht hat>
- **Was gut lief**: <1-2 Sätze>
- **Was nicht klappte**: <1-2 Sätze>
- **Nachbearbeitung nötig bei**: <Dateien oder Logik>
- **Autor**: <Teammitglied>
```

## Einträge

## 2026-05-03 · Value-Alpha-Potential-Modell — TDD-Implementation (Branch `feat/value-alpha-potential-impl`, stacked auf #62)
- **Agent**: Claude Code (Opus 4.7), Main-Context.
- **Scope**: Drittes von 4 ausstehenden Quant-Modellen aus PR #26-Redesign. `ValueAlphaPotentialModel` ersetzt `NotImplementedError`-Skeleton durch Rolling-Max-Alpha-Mean-Reversion: `alpha = pct_change(63) - benchmark.pct_change(63)`, `rolling_max = alpha.rolling(252, min_periods=68).max()`, `potential = rolling_max - alpha`. 7 Tests (Constants, Past-Star vs. Constant, At-Peak-Today/Negative-Potential-Edge-Case, Determinismus, Empty, Insufficient, Single-Ticker), **alle 7/7 grün beim ersten Run**. Volle Suite: 164 passed / 1 skipped, mypy strict + ruff format/check clean.
- **PR-Strategie**: PR #63 stacked auf `feat/trend-momentum-impl` (PR #62), das wiederum auf #61 stacked. Drei-Stufen-Stack. Plan: nach #61-Merge → `gh pr edit 62 --base main`; nach #62-Merge → `gh pr edit 63 --base main`.
- **Was gut lief**:
  - **3. Modell, 3. mal beim ersten Run grün** (Diversification: 5/6, dann 6/6 nach Zero-Variance-Fix; Trend Momentum: 8/8; Value Alpha Potential: 7/7). Spec-First-Disziplin zahlt sich aus — die `2026-04-28-quant-mvp-models.md`-Spec macht alle Edge-Cases explizit, sodass Tests + Impl in der gleichen Mental-Model-Stunde fertig sind.
  - **At-Peak-Test als Spec-Edge-Case-Anchor**: Die Spec sagt explizit „Negativer potential: Aktuelles Alpha über Rolling-Max → gültiger Score, wird normal gerankt." `test_at_peak_today_yields_negative_potential` testet genau das — keine Ranking-Regression bei Edge-Score-Werten. Würde bei „Tests-after" wahrscheinlich vergessen werden.
- **Was nicht klappte**: 
  - **Nichts (zum ersten Mal in der Wave)** — kein Format-Trap, kein Edge-Case-Bug, keine ruff/mypy-Iteration. Der Reflex `ruff format` + `ruff check` als CI-Mirror vor Push ist jetzt eingebaut.
- **Methodisches Mini-Learning**: **Stacked-PRs sind kein Drama, wenn der Diff sauber bleibt.** Drei Branches in der Pipeline (`feat/diversification` → `feat/trend-momentum` → `feat/value-alpha-potential`) bedeuten dreimal `gh pr edit --base main` nach den jeweiligen Merges. Das ist Buchhaltungsaufwand, kein Coding-Aufwand. Der Trade-off lohnt sich gegenüber „warten bis #61 merged, dann erst #62 starten" — wir produzieren 3× so schnell, der Reviewer entscheidet die Reihenfolge.
- **Token-Kosten**: ~12k Tokens Opus 4.7; ~0.25 USD.
- **Autor**: Fabia Holzer (mit Claude Code)

## 2026-05-02 · Trend-Momentum-Modell — TDD-Implementation (Branch `feat/trend-momentum-impl`, stacked auf #61)
- **Agent**: Claude Code (Opus 4.7), reine Main-Context-Arbeit (kein Subagent — kompakter TDD-Cycle).
- **Scope**: Zweites von 4 ausstehenden Quant-Modellen aus PR #26-Redesign. `TrendMomentumModel` ersetzt `NotImplementedError`-Skeleton durch EWMA-basierte Implementation: `prices.pct_change().sub(benchmark.pct_change()).ewm(halflife=63, min_periods=32).mean()` → höchster Score = Rang 1. 8 Tests (Constants, Outperformer-Golden, Identical-Prices-Tie, Recent-Outperformance-EWMA-Halflife-Verifikation, Determinismus, Empty, Insufficient, Single-Ticker), alle grün **beim ersten Run**. Volle Suite: 159 passed / 3 skipped, mypy strict + ruff format/check clean.
- **PR-Strategie**: PR #62 stacked auf `feat/diversification-impl` (Base = #61's Branch), weil pyproject.toml-Deps (pandas/numpy/sklearn) noch nicht in main. Plan: nach #61-Merge `gh pr edit 62 --base main` für sauberen Basiswechsel.
- **Was gut lief**:
  - **TDD-Disziplin: 8/8 grün beim ersten Run**, kein Edge-Case-Bug. Spec war detailliert genug (`docs/specs/2026-04-28-quant-mvp-models.md §3` + Redesign-Spec), dass keine Design-Entscheidungen mid-flight nötig waren.
  - **EWMA-Halflife-Verifikations-Test als spezifischer Behavior-Anchor**: `test_recent_outperformance_weighted_higher` konstruiert zwei Ticker mit *gleicher* Gesamt-Outperformance, aber unterschiedlicher Recency. EWMA mit halflife=63 muss B (recent) höher ranken als A (uniform). Das ist nicht „ein Test der Formel", sondern ein Test der **Spec-Behauptung** „Heute = volles Gewicht, vor 63d = 50%". Genau die Kategorie Test, die bei Tests-after meist fehlt, weil sie nicht aus dem Code abgelesen werden kann.
  - **Lokal CI-Mirror als Reflex**: Diesmal vor Push `ruff format --check` zusätzlich zu `ruff check` gelaufen — Format-Issue im Test-File gefunden + behoben **vor** dem Push. PR #61 hatte das nicht und CI war rot — Lehre direkt umgesetzt.
- **Was nicht klappte**: 
  - **Anfangs Format-Trap erneut**: erster `ruff format --check`-Run (vor Push) zeigte `test_trend_momentum.py` als unformatiert — pandas-DataFrame-Konstruktor multi-line-Style. Reformat-Run + Re-verify innerhalb 30s. **Lehre verfestigt: `ruff format` ≠ `ruff check`, immer beide.**
- **Methodisches Mini-Learning**: **Behavior-Tests > Formel-Tests.** Der EWMA-Halflife-Test prüft *was die Spec verspricht* (Gewichtung), nicht *was der Code tut* (`.ewm(halflife=63)`). Das ist Spec-vs-Code-Asymmetrie als Test-Pattern: wenn der Code irgendwann auf andere Halflife-Werte umgestellt würde, würde der Test die Spec-Verletzung fangen. Dieselbe Idee wie Sheylas Schema-vs-Entity-Asymmetrie in PR #54.
- **Token-Kosten**: ~15k Tokens Opus 4.7; ~0.30 USD.
- **Autor**: Fabia Holzer (mit Claude Code)

## 2026-05-02 · Diversification-Modell — TDD-Implementation (Branch `feat/diversification-impl`)
- **Agent**: Claude Code (Opus 4.7), reine Main-Context-Arbeit (kein Subagent — klassischer Tight-Loop-TDD-Cycle).
- **Scope**: Erstes der 4 noch ausstehenden Quant-Modelle aus dem Redesign-PR #26 vollständig implementiert. `DiversificationModel` ersetzt das `NotImplementedError`-Skeleton in `backend/domain/models/diversification.py` durch die in der Spec festgelegte Ledoit-Wolf-Shrinkage-Kovarianz-Berechnung mit `score = 2 / (annualisierte_vola + avg_korrelation)`. 6 Tests (Golden-Dataset 3-Ticker, Determinismus, leeres Universum, Single-Ticker, < 30 Datenpunkte, Zero-Variance-Ticker), alle grün. Pandas + numpy + scikit-learn neu in `pyproject.toml`-Deps aufgenommen. Volle Suite: 153 passed / 5 skipped, mypy strict + ruff clean.
- **Was gut lief**:
  - **TDD-Disziplin echt eingehalten**: Test-File komplett geschrieben, RED gesehen (6/6 fail mit `NotImplementedError`), erst dann Implementation — und die Implementation hatte beim ersten Run 5/6 grün, der eine Fehler war ein **echter Spec-Insight**: Ledoit-Wolf-Shrinkage glättet die Diagonale, also kann man Zero-Variance-Ticker nicht aus der geshrinkten Cov-Matrix erkennen. Pre-Check auf Roh-Returns-Std hinzugefügt. **Hätte bei "Tests after" niemals gefunden**, weil das Verhalten plausibel aussieht.
  - **Spec-Treue**: Formel exakt aus `2026-04-28-quant-mvp-models.md §5` übernommen, nicht aus dem Gedächtnis rekonstruiert (CLAUDE.md-Anti-Pattern bewusst gemieden).
  - **PR-Workflow korrekt von Anfang an**: Diesmal sofort `git checkout -b feat/diversification-impl` von aktuellem `main`, kein Direkt-Commit-auf-Main-Faux-Pas wie bei PR #26.
- **Was nicht klappte**:
  - **Pandas/numpy/sklearn waren nicht in `pyproject.toml`**, obwohl lokal installiert. Erst beim Schreiben der Tests aufgefallen. Lehre: bei neuer Domain-Library zuerst `pyproject.toml`-Eintrag prüfen, sonst CI grün lokal aber rot in GitHub Actions.
  - **Pythonkonvertierung von numpy-Skalaren zu `float`** an mehreren Stellen nötig, damit mypy strict happy ist. Mini-Friction, aber lehrreich: numpy-Typen leaken sonst in den Domain-Layer.
- **Methodisches Mini-Learning**: **Der Wert des "Verify RED"-Steps ist real.** Hätte ich die Tests nach der Implementation geschrieben, hätte der Zero-Variance-Edge-Case "passend zur Implementation" ausgesehen und das Bug wäre durchgerutscht. Test-First zwingt zur unabhängigen Spec-Prüfung.
- **Token-Kosten**: ~25k Tokens Opus 4.7; ~0.50 USD.
- **Autor**: Fabia Holzer (mit Claude Code)

## 2026-04-27 · Quant-Models-Redesign (PR #26, Commits `7f93095` bis `d62e719`)
- **Agent**: Claude Code (Opus 4.7) + 1 Recherche-Sub-Agent (claude-code-guide) für Daten-Feasibility-Check
- **Scope**: Quality AI + Anti-Cyclical aus dem MVP entfernen, Trend Momentum + Value Alpha Potential rein. Spec geschrieben (`2026-04-27-quant-models-redesign.md`, 237 Z.), ADR 0005 (90 Z.), Design-Spec/README/Frontend/Narrative-Engine/MCP-Spec konsistent durchpatcht (5 Files, 45 +/− 34), Skeleton-Domain-Code für 5 Modelle + 22 grüne / 7 skipped Tests, env-Migration `FINNHUB_API_KEY` → `FMP_API_KEY` im `.env.example`. Alles auf Feature-Branch, PR #26 für Review offen.
- **Was gut lief**:
  - Spec-First-Disziplin gehalten: nach erstem Plan-Vorschlag mehrfach iteriert (5→4→5 Modelle, FMP-Free vs. Starter, Diversification rein/raus), bevor erste Codezeile geschrieben wurde. Vier Iterationen Daten-Feasibility hatten direkten Einfluss auf den finalen Modell-Mix — Schreiben wäre ohne diese Vorarbeit Nacharbeit gewesen.
  - Sub-Agent für Recherche zu Yahoo/FMP-Tier-Limits, statt Trainingswissen zu erraten — die "FMP Free liefert kein Historical"-Erkenntnis war der entscheidende Punkt, der Quality AI gekippt hat.
  - mypy-strict + ruff im Skeleton ohne Workarounds clean — beim ersten Versuch flaggte mypy ein `# type: ignore[arg-type]`, das durch ein `model_validate({...})` ersetzt wurde (saubere Lösung statt Stummschaltung).
  - PR-Disziplin: nach Initial-Commit auf `main` korrigiert, alles auf Feature-Branch verlagert, PR mit Test-Plan und To-Do-Liste angelegt — User behielt jederzeit Review-Kontrolle.
- **Was nicht klappte**:
  1. **Erster Commit ging direkt auf `main`.** AGENTS.md §4 verlangt PR-only — Verstoss innerhalb 5 Min nach Spec-Commit. User hat's gemerkt, ich habe per `git reset --soft HEAD~1` den Commit aus `main` entfernt und auf `feat/quant-models-redesign` verschoben. Lehre: **Branch-Strategie vor erstem Commit aktiv prüfen, nicht nach gut Glück auf Default-Branch arbeiten.**
  2. **PowerShell-PATH-Falle nach `winget install gh`.** `gh.exe` lag installiert da, aber die laufende PowerShell-Session kannte den PATH-Eintrag nicht — drei Iterationen mit User, bis ich die Diagnose machte.
  3. **Daten-Feasibility-Check kam zu spät.** Die ersten zwei Konversations-Runden hätten direkt klären müssen, dass Quality AI mit FMP Free nicht geht.
  4. **`.env`-Editier-Konflikt.** Beim Migrieren der lokalen `.env` hatte der User das File parallel selbst editiert.
- **Nachbearbeitung**: keine bisher; PR ist offen, hängt an menschlichem Review.
- **Methodisches Mini-Learning**: **Spec-First spart eindeutig — aber Spec-First UND Branch-First muss als gemeinsamer Reflex sitzen.**
- **Token-Kosten**: ~120k Tokens (Opus 4.7 + 1 Sub-Agent-Call à ~12k); etwa 4 USD.
- **Autor**: Fabia Holzer (mit Claude Code)

## 2026-04-26 · #19 Implementation — Build-Steps 6-8 (PR #25, Continuation)
- **Agents**: Claude Code (Opus 4.7) im Haupt-Context für Wave 6 (LLMClient) + Wave 7 (Exception-Handler); 1 Sub-Agent (Sonnet 4.6) für Wave 8 (Admin-Endpoint, weil grösserer Scope mit 9 Files + 11 Tests). Bewusste Routing-Entscheidung: Tight-Loop-TDD bleibt im Haupt-Context, gut-spezifizierte Multi-File-Bauarbeit geht an den Subagent.
- **Scope**: Drei zusätzliche Build-Steps in derselben PR #25 statt Stacked-PR oder Self-Merge nach 2 h Review-Stille. `LLMClient`-Wrapper für Anthropic + Voyage mit chars/4-Estimation und SDK-fan-out, `BudgetCapExceeded`-FastAPI-Handler mit `Retry-After`-Header (Sekunden bis Monatswechsel UTC), `GET /api/v1/admin/costs`-Endpoint mit X-API-Key-Auth (constant-time compare) + Pydantic-Response-Schema + neue Env-Vars (`BUDGET_CAP_USD`, `BUDGET_CAP_THRESHOLD`). 86 Tests gesamt (war 75; +11 neue), Mypy + Ruff clean. PR #25 enthält jetzt Build-Steps 1-8 von 11.
- **Was gut lief**:
  - **PR-Continuation-Entscheidung**: Drei Optionen (PR erweitern / Stacked-PR / Selbst-Merge nach 2 h) explizit gegenübergestellt mit Pros/Cons, **Empfehlung formuliert** (PR erweitern, weil Andrea noch keinen Review gestartet hatte und Stacked-Komplexität bei 3 Folge-Commits nicht gerechtfertigt). Sheyla bestätigte. **Lektion**: bei jedem Workflow-Bruch nicht stillschweigend Default wählen, sondern Trade-Offs sichtbar machen.
  - **Subagent-Routing-Entscheidung explizit gemacht**: Waves 6-7 blieben im Haupt-Context, weil TDD-Cycles vom Tight-Loop leben (Test schreiben → Docker-Run → Code → Run, in 30-Sekunden-Cycles). Wave 8 ging an Sonnet-Subagent, weil 9 Files + Schema + Auth-Dep + zwei Test-Files in einem Wave die Main-Context-Hygiene gefährdet hätten. **Heuristik**: Main-Context = iterative Entwicklung mit Run-Feedback, Subagent = Multi-File-Bauarbeit nach klarer Vorgabe.
  - **Subagent-Prompt als Vertrag**: Der ~200-Zeilen-Prompt für Wave 8 spezifizierte alle 7 Files (Schema, Router, Dep, Config-Update, .env-Update, Wire-Up, Tests) inklusive Pydantic-Klassen-Felder, SQL-Queries-Wortlaut, Auth-Comparison-Methode, Test-Cases pro File. Subagent lieferte 86/86 Tests grün, Mypy/Ruff clean, **2 explizit dokumentierte Deviations** (von `Header(...)` auf `Header(default=None)` für 401-statt-422-Auth-Fehler; Python-side sortieren zusätzlich zu SQL-ORDER-BY für Test-Robustheit). **Beide Deviations defensiv und sinnvoll**, vom Subagent von sich aus gemeldet — genau das Verhalten, das man bei delegierten Aufgaben sehen will (transparente Abweichungen statt stille Überraschungen).
  - **Trust-but-Verify-Pattern bewährt**: Nach Subagent-Run direkt `git log` + `git diff --stat` + `pytest` + `mypy` + `ruff` als Sanity-Checks; alle grün. Keine Read-back-zu-tief-Verifikation nötig, weil die Quality-Gates objektiv sind.
- **Was nicht klappte**:
  - **Fast über die Tagesgrenze**: Implementations-Session ging deutlich länger als geplant (ursprünglich „erste 5 Build-Steps", dann Continuation auf 8). Ehrlicher: bei Spec-Implementation gibt's Sog-Effekt — wenn alles grün läuft, ist die Versuchung gross, „nur noch eine Wave" zu machen. Das ist normalerweise gut (Momentum), aber bei dichten Tagen muss bewusst gestoppt werden.
- **Lektion (für die 40%-Achse)**:
  **Routing-Disziplin: Main-Context für TDD-Tight-Loops, Subagent für Multi-File-Bauarbeit nach klarer Vorgabe.** Beide haben einen Sweet-Spot. Wave 8 als Subagent dispatched zu haben war richtig: 9 Files in einem Subagent-Run sind effizienter als 9 sequentielle Edit-Run-Read-Cycles im Haupt-Context. Aber Waves 6-7 als Subagent zu dispatchen wäre falsch gewesen — die TDD-Cycles brauchen sofortige pytest-Run-Feedback, was Subagent-Roundtrips verzerren würde. **Heuristik**: wenn der nächste Schritt von einem Run-Output abhängt (Test-Output, Mypy-Output, Browser-State), bleib im Haupt-Context. Wenn der Schritt eine Reihe gut-definierter File-Änderungen ist die zusammen committed werden, dispatche.
- **Methodisches Mini-Learning**: Subagent-Deviations dokumentieren ist nicht „Nice-to-have", sondern essenziell für Trust-but-Verify. Ein Subagent der stille Deviations einbaut ist gefährlicher als einer der scheitert — Scheitern ist sichtbar, Stille nicht. Bei zukünftigen Subagent-Prompts explizit fordern: "Any deviations from this prompt with reasoning". Hat hier doppelt funktioniert.
- **Autor**: Sheyla Sampietro (mit Claude Code + Sonnet-Subagent für Wave 8)

## 2026-04-26 · #19 Implementation — Build-Steps 1-5 von 11 (PR #25)
- **Agent**: Claude Code (Opus 4.7), reine Main-Context-Arbeit. **Kein Subagent** dieses Mal — die TDD-Schleife (Test schreiben → in Docker laufen lassen → minimal implementieren → wieder laufen) lebt vom Tight-Loop, der Subagent-Roundtrips würde abwürgen.
- **Scope**: Erste Hälfte der Spec-Implementation: `BudgetCapExceeded` (Domain), `pricing.py` mit `ModelPricing`-Dataclass + Registry (Infrastructure), `LLMCallLogORM` SQLAlchemy-Modell + Alembic-Migration (Persistence), `CostTracker` Application-Service mit `check_cap`/`record`. 60 Tests gesamt (24 neue), alle grün, Ruff + Mypy clean, Migration mit upgrade+downgrade-Roundtrip auf Live-DB verifiziert. Folge-PR baut darauf den `LLMClient`-Wrapper, FastAPI-Handler, Admin-Endpoint + Config-Anbindung.
- **Was gut lief**:
  - **Spec-Detailgrad zahlt sich aus**: Weil PR #24 alle fünf Architektur-Entscheidungen explizit gemacht hatte (Wrapper-Pattern, Audit-Log, chars/4, Kalender-Monat UTC, 503-Mapping), gab es während der Implementation **null Design-Entscheidungen mid-flight**. Jeder Wave-Schritt war: Spec lesen → Test schreiben → run → Code → run → commit. Die Spec war Map, nicht nur Konzept.
  - **TDD-Disziplin durchgehalten**: 5 Waves × (RED → GREEN → next Wave). Bei jedem Wave wurde der Test ZUERST geschrieben, ZUERST laufen gelassen (must fail wegen ImportError oder fehlendem Modul), dann Implementation. Keine Versuchung, "schnell den Code zu schreiben, Test kommt nach". CLAUDE.md-Regel ist genau dafür da — sie ist anstrengend in dem Moment, aber das resultierende Vertrauen ist real.
  - **Mock vs Real-DB-Pragmatik**: Boundary-Tests von `check_cap` via Monkey-Patch von `_current_month_usd` waren die richtige Wahl — schnell, präzise, isoliert. Eine echte DB-Test-Fixture wäre für 6 Boundary-Cases Overkill gewesen. Die SUM-SQL-Roundtrip-Verifikation kommt im Folge-PR mit den anderen DB-touching Tests.
  - **Migration smoke-test mit downgrade-Roundtrip**: `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` — das Drei-Schritt-Muster fängt asymmetrische Migrationen (upgrade funktioniert, downgrade ist kaputt) sofort. Standard-Practice, aber leicht zu vergessen wenn man's eilig hat.
- **Was nicht klappte**:
  - **Pyproject.toml-im-Container-Issue erkannt aber nicht gefixt**: Die Tests im Container müssen mit `-o asyncio_mode=auto` aufgerufen werden, weil die Pytest-Config aus `pyproject.toml` nicht greift (Dockerfile mounted nur `backend/`, nicht den Repo-Root). CI ist davon nicht betroffen (installiert via `pip install -e .[dev]`). **Bewusste Scope-Disziplin**: bug erkannt, in PR-Body geflaggt, aber nicht in dieser PR gefixt — sonst wird's ein PR über zwei Themen.
  - **Pricing-Werte sind Best-Estimate**: Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5), Voyage-3-large ($0.18) — aus Training-Daten erinnert, nicht live verifiziert gegen `https://www.anthropic.com/pricing` und `https://docs.voyageai.com/docs/pricing`. Im Modul-Docstring + Commit-Message als verifikations-pflichtig markiert. Die Architektur ist davon unberührt; nur das Single-Source-of-Truth-Constant muss vor Production-Deploy gegengeprüft werden.
- **Lektion (für die 40%-Achse)**:
  **Spec-Qualität bestimmt Implementations-Tempo direkt.** Die Wave-Geschwindigkeit (5 Waves in einer Session, jede mit RED-GREEN-Zyklus + Tests + Lint + Commit) war nur möglich, weil PR #24 jede Architektur-Entscheidung **vorab** geschlossen hatte. Hätte die Spec irgendwo "TBD" oder vage Optionen offen gelassen, wäre jeder Wave eine Mini-Brainstorming-Session geworden. Heuristik: **wenn die Spec den nächsten Wave nicht in 3 Sätzen klar macht, ist die Spec nicht fertig — schreib sie zuerst zu Ende, sonst zahlst du den Preis 5× während der Implementation**.
- **Methodisches Mini-Learning**: Container-/CI-Asymmetrien explizit notieren statt zu fixen. Das `pyproject.toml`-im-Container-Issue ist ein klassischer Yak-Shaving-Trigger — "ich fix das schnell" wird zu zwei Stunden Dockerfile-Debug. Stattdessen: in PR-Body geflaggt, separater Issue-Kandidat, weiter mit Hauptaufgabe.
- **Autor**: Sheyla Sampietro (mit Claude Code)

## 2026-04-25 · Spec für Issue #19 — Budget-Cap & Cost-Tracking (PR #24)
- **Agents**: Claude Code (Opus 4.7) im Haupt-Context für strukturiertes Brainstorming + Verifikation + Git-Flow; 1 Sub-Agent (Sonnet 4.6) für die 643-zeilige Spec-Schreibarbeit. Gleiches Routing-Pattern wie bei ADR-0005, bewährt.
- **Scope**: Implementations-Spec für das Budget-Cap-Feature aus ADR-0004 §7. Q-by-Q-Brainstorming durch fünf Architektur-Entscheidungen: (1) Wrapper-Client vs. expliziter Guard-Block, (2) Audit-Log vs. aggregierter Counter, (3) chars/4-Estimation vs. SDK-`count_tokens`, (4) Kalender-Monat UTC vs. Rolling-30-Days, (5) HTTP-503 vs. 402/429. Pro Frage: Optionen mit +/- gegenübergestellt, Empfehlung markiert, Sheyla wählte. Spec dann an Sonnet-Subagent delegiert mit kompletter Vorab-Spezifikation aller fünf Entscheidungen + Section-Outline + Style-Referenzen.
- **Begleitende Team-Hygiene heute (kein eigener Eintrag)**: PR #9 (Andreas erster PR, 4 Tage offen) reviewed + approved + gemergt; PR #23 (ADR-0005, 3 Tage Review-Stille) selbst gemergt; Issue #16 (CORS-Tightening) selbst im Render-Dashboard erledigt + dokumentiert geschlossen; #22 auto-closed via PR-23-Merge.
- **Was gut lief**:
  - **Ein-Frage-pro-Turn-Disziplin**: keine Wall-of-Decisions. Nach jeder Frage hat Sheyla die Implikation wirklich verstanden und konnte begründet wählen statt zu nicken. Die Disziplin der Brainstorming-Skill — fragmentieren statt batchen — erzwingt gründliches Nachdenken auf beiden Seiten.
  - **Subagent-Prompt-Qualität als Filter für eigenes Denken**: Bevor ich den Sonnet-Subagent dispatchen konnte, musste ich alle fünf Entscheidungen + Section-Outline + Style-Regeln in einen ~80-Zeilen-Prompt packen. Wo der Prompt vage wurde, war meine eigene Architektur-Klarheit unzureichend. Das Schreiben des Prompts war damit selbst die letzte Designschicht — der Subagent musste nichts mehr „designen", nur dokumentieren.
  - **Spec-Output direkt implementierbar**: keine TBDs, keine offenen Fragen, alle Mermaid-Diagramme korrekt, SQL exakt, Decimal-für-Geld durchgehend, Build-Order mit expliziten Abhängigkeiten. Sheyla muss nicht in einer zweiten Iteration nachschärfen.
  - **Datums-Konventions-Korrektur durch Sheyla**: sie hat gemerkt, dass die alten Phase-3-Specs mit Future-Datum (`2026-04-28-*`) falsch benannt waren — Files wurden am 21./22. April geschrieben, nicht am 28. Statt blind weiter mit dem falschen Pattern, hat sie hinterfragt. Resultat: heute → real-date-Konvention etabliert, alte Files unbenannt belassen (Rename = Commit-Noise für 0 Funktionalitäts-Gewinn). Genau die Art „Konvention bewusst dokumentieren statt implizit ererben"-Moment, die in die 40%-Achse einzahlt.
- **Was nicht klappte**:
  - **Falsche Datums-Konvention vier Tage durchgerutscht**: hätte beim allerersten Phase-3-Spec auffallen müssen. Der heutige Diskussionsmoment war ein Glücksfall — ohne Sheylas Frage hätten wir den Fehler unbemerkt fortgepflanzt. Heuristik: bei jedem Datei-Naming-Pattern aktiv prüfen, ob das Datum die Erstellung oder eine geplante Zukunft beschreibt; nur Erstellung ist git-konsistent.
- **Lektion (für die 40%-Achse)**:
  **Strukturiertes Brainstorming dominiert „direkt drauflos schreiben".** Nach den fünf Entscheidungs-Frage-Runden hatte die Spec keine versteckten Annahmen, keine vagen Stellen, keine Design-Holes. Der Subagent musste nicht „kreativ" sein. Das ist der Unterschied zwischen einem Spec-Draft, der noch eine zweite Iteration braucht, und einem, der direkt in einen Implementations-Plan überführbar ist. **Heuristik**: vor jedem Subagent-Dispatch alle Architektur-Entscheidungen explizit gemacht haben. Wenn man dem Agent keinen klaren Auftrag formulieren kann, ist das eigene Denken noch nicht fertig — der Subagent ist hier ein Lackmustest.
- **Methodisches Mini-Learning**: Frage-pro-Turn ist nicht „nett zum User" — sondern Pflicht-Tool gegen die eigene Versuchung, die Spec gleich zu schreiben statt sie erst durchzudenken. Die Geduld zahlt sich exponentiell aus, je grösser die Spec — bei 643 Zeilen wäre eine zweite Iteration teurer gewesen als die fünf Frage-Runden zusammen.
- **Autor**: Sheyla Sampietro (mit Claude Code + Sonnet-Subagent)

## 2026-04-22 · ADR-0005 — Datenquelle für Quant-Fundamentaldaten (PR #23, Closes #22)
- **Agents**: Claude Code (Opus 4.7) im Haupt-Context für Brainstorming, Verifikation und Git-Flow; 1 Sub-Agent (Sonnet 4.6) für die reine ADR-Schreibarbeit.
- **Scope**: Entscheidungsprozess für die Fundamentaldaten-Quelle der 8 Quality-Classic-Metriken. Brainstorming von 4 Optionen (yfinance-live / CSV-only / Hybrid / Alpha-Vantage-oder-Finnhub), Wahl des Hybrid-Ansatzes (committed CSV-Snapshot als Wahrheit + yfinance-Adapter nur für manuellen Pre-Presentation-Refresh). Schreiben von `docs/adr/0005-data-source-quant-fundamentals.md` im bestehenden ADR-Stil, minimale Klarstellung in §13 des Haupt-Design-Dokuments, PR mit Fabia + Andrea als Reviewer. Begleitet von Wechsel von direct-to-main auf PR-Flow (Phase-1-Infra-Firefighting-Modus ist vorbei, jetzt hat das Team Review-Verantwortung).
- **Was gut lief**:
  - **Model-Routing bewusst gesetzt**: Opus 4.7 führte die Trade-off-Analyse und das Spec-Navigieren (Kontext aus 681-Zeilen-Haupt-Spec + Issue-Rationale synthetisieren). Die reine Template-gehorsame Schreibarbeit — ein ADR nach dem exakten Muster von 0001/0002 verfassen — wurde an einen Sonnet-Subagent delegiert. Das senkte den Token-Footprint im Haupt-Context merklich und hielt die Aufmerksamkeit für die Review-Entscheidung frei.
  - **Trust-but-Verify nach Subagent-Run**: Vor dem Commit wurden das generierte ADR und der Diff der §13-Änderung gelesen. Keine Halluzinationen, Format exakt an den Vorbildern, Paragraph-Insertion minimal-invasiv.
  - **Brainstorming-Disziplin**: 4 Optionen wurden mit +/- bewertet bevor eine empfohlen wurde — Benutzerin konnte A/B/C einfach abwägen und C auswählen, kein "hier ist meine Einzellösung, nimm oder lass"-Fallstrick.
- **Was nicht klappte**:
  - **Verdeckte Spec-Inkonsistenz wurde erst beim Lesen sichtbar**: §13 des Haupt-Design-Dokuments setzte `yfinance` als primäre Laufzeit-Quelle voraus, Issue #22 empfahl aber explizit einen CSV-Snapshot. Diese Spannung hätte schon bei der Issue-Erstellung auffallen können. Retroaktive §13-Klarstellung war die Konsequenz — nicht tragisch, aber ein Hinweis, dass Specs und Issues konsistent-gehalten werden müssen, wenn beide Design-Aussagen treffen.
- **Lektion (für die 40%-Achse)**:
  **Model-Routing ist eine reale AI-Engineering-Disziplin.** Reasoning-dichte Arbeit (Options-Abwägung, Risiko-Analyse, Kontext-Synthese) bleibt beim grösseren Modell. Template-gehorsame Schreibarbeit nach bestehendem Muster wird an ein kleineres Modell delegiert. Der Punkt ist nicht primär Kostenersparnis, sondern **Kontext-Hygiene**: der Haupt-Context behält Platz für die Entscheidungen, die wirklich Urteil brauchen. Dieselbe Split-Logik spiegelt PRISMAs eigenes Narrative-Layer-Design wider (AnalystAgent vs. SynthesizerAgent aus dem Multi-Agent-Spec) — das Werkzeug-Muster matched das Produkt-Muster.
- **Methodisches Mini-Learning**: Beim Wechsel von direct-to-main auf PR-Flow den Trigger-Punkt explizit machen. Hier: sobald das Team zugewiesene Issues hat und der Code-/Design-Change ihre Arbeit beeinflusst, ist der PR-Review-Loop nicht nur Hygiene sondern Team-Dependency-Management. Die Grenze sauber zu benennen schützt davor, aus Bequemlichkeit weiter direkt auf `main` zu schieben.
- **Autor**: Sheyla Sampietro (mit Claude Code + Sonnet-Subagent)

## 2026-04-21 · Render-Deployment Phase 1 — 4 Commits bis End-to-End-grün (Commits `7b2de04` bis `87e2407`)
- **Agent**: Claude Code (Opus 4.7)
- **Scope**: Blueprint-basiertes Deployment (DB + Backend + Frontend) auf Render's Free-Tier. Vier aufeinanderfolgende Produktions-Deploy-Versuche, drei davon an Details der Render-Plattform gescheitert bevor der Fourth Green wurde.
- **Was gut lief**:
  - Die Render-Logs waren in jedem Fehlerfall konkret genug, um die Root-Cause nach einmal Lesen zu isolieren — kein rätselhaftes "works on my machine"-Debugging nötig.
  - DATABASE_URL-Scheme-Rewrite via pydantic-Validator (`postgresql://` → `postgresql+asyncpg://`) war proaktiv eingebaut — sonst wäre ein fünfter Deploy-Cycle nötig gewesen.
  - Commit-Disziplin blieb trotz Zeitdruck sauber: ein Fix pro Commit, aussagekräftige Messages, nichts gebündelt.
- **Was nicht klappte — drei Render-spezifische Stolpersteine**:
  1. **`preDeployCommand` ist Paid-Tier-only** — der Agent hat das Field gesetzt um Alembic-Migrationen vor dem App-Start zu triggern, aber Render's Blueprint-Validator hat den Deploy sofort abgelehnt: "preDeployCommand is not supported on free plan". Fix: Migrations inside Container-Start-Sequence.
  2. **`dockerCommand: "sh -c 'alembic upgrade head && exec uvicorn ...'"` exit 127 "not found"** — Render's YAML-Parser übergibt den gesamten String als EINEN argv-Eintrag (nicht wie die Shell `sh -c` + zwei weitere Args). Docker sucht dann nach einem Executable namens `sh -c 'alembic …'` (mit Leerzeichen im Namen) und findet es natürlich nicht. **Fix**: Start-Sequenz in ein `scripts/backend-start.sh` auslagern und nur ein `CMD ["/app/backend-start.sh"]` im Dockerfile — dann ist der argv-Split wieder sauber. Render wollte gar kein `dockerCommand`-Override mehr.
  3. **`NEXT_PUBLIC_API_URL` via `fromService.property: host` liefert nur den Hostname — ohne `https://`** — das Frontend lud, aber der Backend-Badge zeigte HTTP 404. Ursache: Der Client-Code machte `${API_BASE_URL}${path}` = `"prisma-backend-7ai7.onrender.com/health"`. Der Browser interpretiert eine schemelose URL als *relativen Pfad* → Request ging an `https://prisma-frontend-jrto.onrender.com/prisma-backend-7ai7.onrender.com/health` → 404. Render bietet keine "scheme prepend"-Option für `fromService`. **Fix**: Backend-URL hardcoden (`value: https://prisma-backend-7ai7.onrender.com`). Einmalig ungünstig, aber semantisch klar — und `NEXT_PUBLIC_*` wird bei Next.js sowieso Build-Time in das Bundle gebacken, d.h. dynamische Service-Refs helfen hier architektonisch nichts.
- **Nachbearbeitung nötig bei**:
  - `render.yaml` (3 × iteriert)
  - neues `scripts/backend-start.sh` als einziger Start-Sequence-Ort
  - `Dockerfile.backend` auf `CMD ["/app/backend-start.sh"]`
- **Lektion (wichtig für die 40%-Achse)**:
  **PaaS-Plattformen haben viele implizite Einschränkungen, die der Agent aus seinem Trainings-Wissen nicht alle kennt.** Tier-Limits, Argv-Parsing-Quirks, Primitives die nur Teile einer URL liefern — diese sind dokumentiert, aber nicht in "einen typischen `render.yaml`"-Beispielen im Trainingscorpus. **Heuristik**: Bei jedem Deploy-Config-Feld mental fragen "was passiert wenn Render das wörtlich so interpretiert?" und "welche Tier-Stufe brauche ich dafür?". Gerade Shell-Semantik-Illusion in YAML-Strings (`dockerCommand: "sh -c '...'"`) ist ein wiederkehrender Fallstrick — **immer als Array-Form oder Script-Datei schreiben, nie als inline-Shell-String**.
- **Methodisches Mini-Learning**: Bei undurchsichtigen PaaS-Bugs ist die schnellste Diagnose-Frage nicht "was ist falsch?" sondern "was genau reicht Render hier ins Child-Process weiter?". Im Zweifel stdout/stderr direkt lesen statt Hypothesen bauen — die Render-Logs haben in allen drei Fällen den korrekten Hint direkt ausgegeben.
- **Autor**: Sheyla Sampietro (mit Claude Code)

## 2026-04-21 · CI stabilisieren — 5 Commits bis grün (Commits `74c558a` bis `78ee56d`)
- **Agent**: Claude Code (Opus 4.7) mit Sub-Agent-Unterstützung beim initialen Scaffold
- **Scope**: Nach dem Foundation-Commit fiel die GitHub-Actions-CI mehrfach um. Ich arbeitete mich durch 5 aufeinanderfolgende Fix-Commits (Backend-Lint → Backend-Format → Frontend-Pfad-Alias → Mypy-Ignore-Komm. → **eigentliche Root-Cause**: fehlende Files im Git).
- **Was gut lief**: 
  - Jeder Fix wurde lokal verifiziert, bevor gepusht wurde (docker compose exec + `ruff check` + `npm run build`)
  - AI-USAGE.md-Eintrag parallel zur Debug-Arbeit gepflegt → Lernschleife während der Reparatur, nicht erst danach
  - Systematisches Vorgehen: CI-Logs lesen → Fehler isoliert reproduzieren → fix → push → beobachten
- **Was nicht klappte — die eigentliche Lektion**:
  Mehrere CI-Runs zeigten `Module not found: Can't resolve '@/lib/utils'` im Frontend. Der **offensichtlich** wirkende Fix war `baseUrl: "."` in `tsconfig.json` zu ergänzen (Next.js path-alias-Konvention). Das stimmte auch — aber der Bug blieb! Erst beim manuellen Reproduzieren mit `docker run node:20-alpine npm run build` — das lokal GRÜN lief — wurde klar: **die Files existierten gar nicht im Git**. Ursache: Der Agent hatte beim Initial-Scaffold einen Python-Template-`.gitignore` generiert. Die Regel `lib/` matched nicht nur das erwartete Python-Build-Directory, sondern auch `frontend/lib/` — und hat damit `utils.ts`, `api/client.ts`, `api/health.ts` silent aus dem Repo geschluckt. Lokal alles OK (Files auf Disk), CI tot (cloned Repo ohne Files).
- **Nachbearbeitung nötig bei**:
  - `.gitignore`: `lib/` → `/lib/` scopen (Root-only); gleiches für `lib64/`
  - `git add frontend/lib/` um bisher ignorierte Files endlich zu committen
  - 2 unused `# type: ignore` Kommentare in Tests entfernen (mypy-strict flaggt sie)
  - 3 Files mit neuerer Ruff-Version nachformatieren
- **Lektion (wichtig für die 40%-Achse)**:
  **AI-generierte Config-Files (`.gitignore`, `.dockerignore`, `.eslintignore`) sind typischerweise Templates, die kontextblind für Subdirectories sind.** Wenn das Projekt mehrere Sprachen/Stacks hat, prüfe jede Regel: matched sie wirklich nur was gemeint war? Die Kosten der Blindheit waren hier 3 Fehldiagnosen + rund 30 Minuten Debugging, bevor ich aufs wirkliche Problem kam. Gute Heuristik für künftige Reviews: **bei Multi-Language-Repos `.gitignore`-Regeln bewusst scopen** (mit führendem `/` für Root-only, oder mit expliziten Pfadpräfixen).
- **Methodisches Mini-Learning**: *Lokal grün, CI rot* = fast immer eine Environment-Diskrepanz. Statt am Code zu zimmern, zuerst prüfen: (1) ist derselbe Code wirklich committed? (2) wird derselbe Stand geclont? (3) ist dieselbe Tool-Version aktiv? Die Versuchung, "einfach noch einen Fix" zu pushen statt die Diskrepanz zu isolieren, hat mich hier 2 Commits gekostet.
- **Autor**: Sheyla Sampietro (mit Claude Code)

## 2026-04-21 · Phase-1 Foundation Scaffold (#1–#7)
- **Agents**: 2 Sub-Agents parallel (voltagent-core-dev:backend-developer + voltagent-lang:nextjs-developer), beide Sonnet. Orchestriert von Claude Code Opus 4.7.
- **Scope**: In einer Session 70 Files (2243 Zeilen) geschrieben: komplettes FastAPI-Backend mit Clean Architecture + async SQLAlchemy + Alembic + Tests, Next.js-14-Frontend mit shadcn/ui + React Query, docker-compose, GitHub Actions CI, Render-Blueprint. End-to-End auf Docker verifiziert (alle Container healthy, Endpoints liefern).
- **Was gut lief**:
  - Parallelisierung war sauber — beide Agents arbeiteten auf disjunkten Directories, kein Konflikt.
  - Strukturell sehr sauberer Code: Clean-Architecture-Schichten eingehalten, Type-Hints durchgängig, strukturierte Outputs, gute Test-Abdeckung im Scaffold.
  - Direktes Abbilden der Spec-Sektionen (Abschnitt 4, 5, 9, 10, 11, 12) in konkrete Dateien ging zuverlässig.
- **Was nicht klappte** (4 Bugs in agent-generiertem Code, alle beim ersten Docker-Build entdeckt):
  1. `pyproject.toml` hatte `build-backend = "setuptools.backends.legacy:build"` — dieses Backend existiert nicht in setuptools. Korrekt: `setuptools.build_meta`. Klassische Halluzination.
  2. `Dockerfile.frontend` nutzte `npm install --frozen-lockfile` — das ist ein Yarn-Flag, npm kennt es nicht. Korrekt: `npm install`.
  3. `Dockerfile.frontend` hatte `COPY --from=builder /app/public ./public 2>/dev/null || true` — Shell-Syntax (Redirects, `||`) funktioniert NICHT in Dockerfile-COPY-Instruktionen. Docker interpretierte `2>/dev/null` und `||` als Quell-Pfade, daher der kryptische Fehler `"/||": not found`. Fix: einfaches `COPY` + leeres `frontend/public/.gitkeep`.
  4. `Dockerfile.backend` fehlte `ENV PYTHONPATH=/app` — ohne das findet Python das `backend`-Package nicht (da es via WORKDIR/app referenziert, aber nicht als installiertes Package).
  5. `backend/config.py` hatte `cors_origins: list[str]` — pydantic-settings v2 versucht für `list[str]` JSON-Decoding des Env-Values BEVOR der field_validator läuft; `http://localhost:3000` ist kein valides JSON. Fix: `Annotated[list[str], NoDecode]` damit pydantic-settings das Raw-String an den Validator durchreicht.
- **Nachbearbeitung nötig bei**: `pyproject.toml` (build-backend), `Dockerfile.frontend` (2 Stellen), `Dockerfile.backend` (PYTHONPATH), `backend/config.py` (NoDecode). Insgesamt ca. 15 Minuten Debugging.
- **Lektion**: Agents produzieren syntaktisch plausiblen, aber real nicht funktionalen Code wenn es um seltene Infrastruktur-Detail-APIs geht (Dockerfile-vs-Shell-Unterschied, pydantic-settings v2 quirks, obscure Build-Backend-Namen). TDD-Prinzip gilt auch für Infrastruktur: **erstmal bauen + hochfahren + anfragen, bevor man den nächsten Layer draufsetzt**. Alles grün erst nach Verifikation.
- **Autor**: Sheyla Sampietro (mit Claude Code + Sub-Agents)

## 2026-04-21 · Initial Scaffold (#0)
- **Agent**: Claude Code (Opus 4.7)
- **Scope**: Komplettes Repo-Scaffolding: Clean-Architecture-Ordnerstruktur, AGENTS.md/CLAUDE.md, CONTRIBUTING.md, .gitignore, ADR-0001 (Tech-Stack), Design-Spec (681 Zeilen) via documentation-engineer Sub-Agent, GitHub-Repo-Erstellung, Branch-Protection, Scrum-Setup.
- **Was gut lief**: Parallele Ausführung von Schreibvorgängen und Git-Operationen sparte merklich Zeit. Sub-Agent für die Design-Spec hat sauber strukturiert und alle Scope-Entscheidungen aus dem Brainstorming festgehalten. Conventional-Commits und Co-Authored-By-Footer konsistent gesetzt.
- **Was nicht klappte**: Erster `gh api`-Call für Branch Protection schlug an Type-Coercion fehl; JSON-Body via stdin war der saubere Workaround. Kein inhaltlicher Fehler, nur API-Syntax-Stolperer.
- **Nachbearbeitung nötig bei**: Noch keine.
- **Autor**: Sheyla Sampietro (mit Claude Code)

<!-- Neue Einträge oben an die Liste anfügen. -->
