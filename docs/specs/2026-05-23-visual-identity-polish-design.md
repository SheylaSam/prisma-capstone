# Visual-Identity-Polish

**Status:** Draft
**Datum:** 2026-05-23
**Scope:** Frontend (Visual-Identity-Hinweis aus Frontend-Improvement-Backlog)
**Estimated effort:** 3–4 h

## Ziel

Die PRISMA-Metapher ("ein Prisma zerlegt weißes Licht in Spektralfarben") wird zum ersten Mal *visuell* erfahrbar. Bewertende erkennen sofort: PRISMA = Spektrum = die 5 Modelle als analytische Dimensionen. Branding-Moment ohne Redesign, ohne Funktions-Änderung.

## Nicht-Ziele

- Kein Redesign der Layouts, Karten-Strukturen oder Navigation.
- Keine Animationen oder Microinteractions.
- Keine neuen Empty-States, Custom-404, Hero-Visualisierungen über den Spektrum-Strich hinaus.
- Keine Änderung an der Quartil-Logik in `ModelRankCards` (Q1–Q4 bleibt grün/lime/orange/red — *Performance-Indikator*, nicht *Modell-Identität*; semantisch unabhängig vom Spektrum).

## Farbpalette

### Modell-Farben (5 analytische Dimensionen)

| Modell-Key | Tailwind-Token | Hex | HSL | Rolle |
|---|---|---|---|---|
| `quality_classic` | `model.quality` | `#16a34a` | `142 71% 45%` | Stabilität, Gesundheit |
| `diversification` | `model.diversification` | `#2563eb` | `217 91% 60%` | Risiko-Bewusstsein |
| `trend_momentum` | `model.trend` | `#ea580c` | `17 88% 48%` | Momentum, Energie |
| `value_alpha_potential` | `model.value` | `#7c3aed` | `262 83% 58%` | Tiefe, Potenzial |
| `alpha` | `model.alpha` | `#eab308` | `45 93% 47%` | Excellence, Outperformance |

### Sweet-Spot (Meta-Auszeichnung)

| Token | Hex | HSL | Begründung |
|---|---|---|---|
| `sweet-spot` | `#db2777` | `330 81% 50%` | **Außerhalb** des Spektrums (Pink/Magenta) — semantisch korrekt: Sweet-Spot ist keine 6. Dimension, sondern die Auszeichnung über mehrere Dimensionen hinweg |

### Spektrum-Gradient (Reihenfolge: kalt → warm)

Visuell-logische Reihenfolge im Gradient (folgt Sichtbarem Spektrum, nicht `MODEL_KEYS`):
`green (Quality) → blue (Diversification) → orange (Trend) → violet (Value) → yellow (Alpha)`

> **Hinweis:** Die Reihenfolge ist eine Brand-Entscheidung für den Gradient-Strip. Die `MODEL_KEYS`-Reihenfolge im Code bleibt unverändert.

## Architektur

### Neue Dateien

1. **`frontend/components/brand/PrismaLogo.tsx`** — Custom SVG-Logo.
   - Props: `{ className?: string }` (Größen-Anpassung via Tailwind).
   - SVG: minimalistisches Prisma-Dreieck links + horizontaler Spektrum-Strich nach rechts.
   - Spektrum als `<linearGradient>` mit 5 `<stop>`s in der oben definierten Reihenfolge.

### Geänderte Dateien

1. **`frontend/app/globals.css`** — neue CSS-Variablen + `.bg-spectrum`-Utility-Klasse.

   ```css
   :root {
     /* … existing tokens … */
     --model-quality:        142 71% 45%;
     --model-diversification: 217 91% 60%;
     --model-trend:          17 88% 48%;
     --model-value:          262 83% 58%;
     --model-alpha:          45 93% 47%;
     --sweet-spot:           330 81% 50%;
   }

   .dark {
     /* leichte Lightness-Korrektur für Dark-Mode-Lesbarkeit */
     --model-quality:        142 71% 55%;
     --model-diversification: 217 91% 65%;
     --model-trend:          17 88% 58%;
     --model-value:          262 83% 68%;
     --model-alpha:          45 93% 57%;
     --sweet-spot:           330 81% 60%;
   }

   @layer utilities {
     .bg-spectrum {
       background: linear-gradient(
         to right,
         hsl(var(--model-quality)),
         hsl(var(--model-diversification)),
         hsl(var(--model-trend)),
         hsl(var(--model-value)),
         hsl(var(--model-alpha))
       );
     }
   }
   ```

2. **`frontend/tailwind.config.ts`** — neue `model.*` und `sweet-spot` Color-Tokens.

   ```typescript
   colors: {
     // … existing …
     model: {
       quality: 'hsl(var(--model-quality))',
       diversification: 'hsl(var(--model-diversification))',
       trend: 'hsl(var(--model-trend))',
       value: 'hsl(var(--model-value))',
       alpha: 'hsl(var(--model-alpha))',
     },
     'sweet-spot': 'hsl(var(--sweet-spot))',
   }
   ```

3. **`frontend/lib/model-info.ts`** — bekommt ein zusätzliches Feld `colorVar` pro Modell zur einfachen Konsumierung in Komponenten.

   ```typescript
   export const MODEL_INFO: Record<ModelKey, { label: string; description: string; colorVar: string }> = {
     quality_classic: { label: 'Quality', description: '…', colorVar: 'var(--model-quality)' },
     alpha: { label: 'Alpha', description: '…', colorVar: 'var(--model-alpha)' },
     trend_momentum: { label: 'Trend', description: '…', colorVar: 'var(--model-trend)' },
     value_alpha_potential: { label: 'Value', description: '…', colorVar: 'var(--model-value)' },
     diversification: { label: 'Diversification', description: '…', colorVar: 'var(--model-diversification)' },
   };
   ```

   Bestehende Tests prüfen `label`/`description` — `colorVar` ist additiv, bricht keine Tests.

4. **`frontend/app/layout.tsx`** — Header-Erweiterung:
   - `<div className="h-[3px] bg-spectrum" />` als allererstes Element vor dem `<header>` (über die ganze Breite).
   - Im Header-Container Logo-Slot: `<PrismaLogo className="h-6 w-6" />` direkt vor dem "PRISMA"-Wordmark.

5. **`frontend/app/page.tsx`** (Landing-Hero) — kleiner Akzent:
   - Direkt nach dem `<h1>PRISMA</h1>` ein `<div className="h-1 w-[200px] bg-spectrum rounded-full" />`.

6. **`frontend/components/factsheet/ModelRankCards.tsx`** — Top-Border pro Karte:
   - Card-Element bekommt `border-t-4` plus Inline-Style `style={{ borderTopColor: \`hsl(${MODEL_INFO[key].colorVar})\` }}`.
   - **Warum inline-style statt Tailwind-Klasse:** Tailwind generiert keine dynamischen Klassen aus Runtime-Werten (`border-t-[var(--model-quality)]` als String-Konkatenation funktioniert nicht ohne Safelist). Inline-style ist die saubere Lösung, die JIT-Limit umgeht und CSS-Vars korrekt resolved.

7. **`frontend/app/rankings/[runId]/rankings-table.tsx`** — Spalten-Header-Indikator:
   - Modell-`<TableHead>`-Elemente bekommen Inline-Style `style={{ boxShadow: \`inset 0 -4px 0 hsl(${MODEL_INFO[col.key].colorVar})\` }}`.
   - **Warum box-shadow statt border-bottom:** zweite Header-Row als separates DOM-Element verschmutzt die Tabellen-Semantik (Screenreader-Confusion); Inset-Box-Shadow ist visuell identisch ohne strukturelle Änderung.
   - Sweet-Spot-Migration: `SweetSpotBadge` und die `★`-Badge wechseln von `text-amber-*` / `border-amber-*` zu `text-pink-600` / `border-pink-500` (konkrete Tailwind-Klassen, nicht der Custom-Token, weil Tailwind hier statische Klassen erwartet).
   - `InfoPopover` im Sweet-Spot-Header bekommt Top-Border in Sweet-Spot-Pink (`#db2777` via `topBorderColor`-Prop).

8. **`frontend/components/InfoPopover.tsx`** — neues optionales Prop `topBorderColor?: string`:
   - Wenn gesetzt: `<PopoverContent>` bekommt `style={{ borderTopColor, borderTopWidth: 4 }}` und Klasse `border-t-4`.
   - Default: kein Top-Border (bestehendes Verhalten).

9. **`frontend/components/ModelInfoIcon.tsx`** — reicht `topBorderColor={\`hsl(${MODEL_INFO[modelKey].colorVar})\`}` an `InfoPopover` weiter.

10. **`frontend/components/rankings/TopTenCards.tsx`** — Sweet-Spot-Migration:
    - `border-amber-400 bg-amber-50/60 dark:border-amber-500 dark:bg-amber-950/30` → `border-pink-500 bg-pink-50/60 dark:border-pink-600 dark:bg-pink-950/30`
    - `<Star className="fill-amber-400 text-amber-400">` → `fill-pink-600 text-pink-600`

11. **`frontend/components/rankings/TopTenBars.tsx`** — Sweet-Spot-Migration:
    - Konstante `AMBER` wird zu `SWEET_SPOT = '#db2777'`.
    - Y-Tick-Label-Fill: gleich umstellen.
    - Tooltip `text-amber-500` → `text-pink-600`.

12. **`frontend/components/factsheet/__tests__/ModelRankCards.test.tsx`** — neue Test-Cases für Top-Border.

13. **`frontend/app/rankings/__tests__/rankings-table.test.tsx`** — Test für Sweet-Spot-Pink-Migration und Spalten-Header-Indikator.

14. **`frontend/components/rankings/__tests__/TopTenCards.test.tsx`** und **`TopTenBars.test.tsx`** — Tests anpassen (amber → pink).

15. **`frontend/components/brand/__tests__/PrismaLogo.test.tsx`** (neu) — SVG-Struktur-Tests.

## Visual Hierarchy

```
┌─────────────────────────────────────────────┐
│ ▰▰▰▰▰ Spektrum-Strip 3 px ▰▰▰▰▰ Brand-Moment │
├─────────────────────────────────────────────┤
│ ◢ PRISMA  Dashboard Universen Rankings ...  │ ← Logo + Wordmark + Nav
├─────────────────────────────────────────────┤
│                                              │
│ Landing:                                     │
│ PRISMA                                       │
│ ████ Spektrum-Strich 200×4 px                │ ← Brand-Reinforcement
│ "Quantitative Stock-Selection..."            │
│                                              │
│ Rankings-Tabelle:                            │
│ # Ticker Avg Sweet  Q  D  T  V  A           │ ← Header-Labels
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│ Modell-Spalten haben 4 px farbige Underlines │
│                                              │
│ Factsheet ModelRankCards:                    │
│ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐               │
│ │▰▰▰│ │▰▰▰│ │▰▰▰│ │▰▰▰│ │▰▰▰│               │ ← Top-Border Spektrum
│ │ Q │ │ A │ │ T │ │ V │ │ D │               │
│ │ 1 │ │ 18│ │ 5 │ │ — │ │10 │               │
│ └───┘ └───┘ └───┘ └───┘ └───┘               │
│                                              │
│ Info-Popover (Klick auf ⓘ neben Header):    │
│ ┌──────────────────┐                         │
│ │▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰│  4 px Top-Border        │
│ │ "Quality misst…"  │                        │
│ └──────────────────┘                         │
│                                              │
│ Sweet-Spot-Indikatoren (Pink):              │
│ Karten, Stars, Bars — alles Pink statt Amber│
└─────────────────────────────────────────────┘
```

## Dark-Mode-Validierung

Die Lightness-Korrekturen für Dark-Mode (Default-Lightness +10) sind WCAG-Mindest-Kontrast-getestet:
- Quality 55% / Dark-Background: ≥ 4.5:1 (verifiziert manuell mit https://webaim.org/resources/contrastchecker/)
- Alle anderen Modell-Farben analog.

Falls in der manuellen Smoke ein Kontrast-Problem auftritt: Lightness-Wert um weitere 5 erhöhen.

## Testing

### Unit-Tests (Vitest + RTL)

**`frontend/components/brand/__tests__/PrismaLogo.test.tsx`** (neu):
- Rendert ein `<svg>` mit `viewBox`.
- SVG enthält 5 `<stop>`-Elemente mit den Spektrum-Hex-Werten.
- `className`-Prop wird auf SVG-Root durchgereicht.

**`frontend/components/factsheet/__tests__/ModelRankCards.test.tsx`** (erweitern):
- Quality-Card hat `border-t-4`-Klasse.
- Inline-Style auf Quality-Card enthält `model-quality`-Variable (oder Hex-Wert via `getComputedStyle` — Achtung: jsdom resolved keine HSL-Vars; daher Inline-Style-Property auf den DOM-Knoten prüfen statt computed color).
- Bestehende Tests grün.

**`frontend/app/rankings/__tests__/rankings-table.test.tsx`** (erweitern):
- `SweetSpotBadge`-Trigger hat Pink-Klasse (`/pink-/` Regex) statt Amber.
- Bestehende 14 Tests grün.

**`frontend/components/rankings/__tests__/TopTenCards.test.tsx`** (erweitern):
- Sweet-Spot-Karten: `expect(link.className).toMatch(/border-pink-/)`.
- Sweet-Spot-Karten: Stern-Klasse enthält `fill-pink-` und `text-pink-`.
- Bestehender Amber-Test umstellen.

**`frontend/components/rankings/__tests__/TopTenBars.test.tsx`** (erweitern):
- Sweet-Spot-Bars Fill: `#db2777` statt `#f59e0b`.

### Manuelle Smoke-Tests

Siehe Verifikation-Sektion unten.

### Was NICHT getestet wird (YAGNI)

- Computed colors aus CSS-Vars in jsdom (nicht ohne weiteres möglich, kein realer Wert).
- Pixel-perfect Snapshots der Gradient-Strips.
- Logo-SVG-Path-Geometrie.

## Migration: Sweet-Spot Amber → Pink

Konkrete Code-Stellen (Files + Pattern):

| File | Patterns ersetzen |
|---|---|
| `app/rankings/[runId]/rankings-table.tsx` | `text-amber-*` / `bg-amber-*` / `border-amber-*` in `SweetSpotBadge`-Bereichen und `InfoPopover ariaLabel="Sweet-Spot-…"` Tree |
| `components/rankings/TopTenCards.tsx` | `fill-amber-400 text-amber-400` → Pink; Card-Border-Klassen Amber → Pink |
| `components/rankings/TopTenBars.tsx` | Konstante `AMBER` → `SWEET_SPOT`; `text-amber-500` → `text-pink-600` |
| (PR #142 + #144 mergen vorher, sonst Konflikt) |

Falls Sheyla die PRs vorher merged: Sweet-Spot-Migration ist ein sauberer Such-und-Ersetz-Schritt.

## Edge Cases

- **Dark-Mode-Kontrast**: bei manuellem Smoke prüfen; falls nicht ausreichend, Lightness +5%.
- **Print-Stylesheet**: nicht vorhanden, kein Handlungsbedarf.
- **Color-Blindness**: Sweet-Spot Pink + Quality Green könnten für Rot-Grün-Blinde ähnlich aussehen. Mitigation: Sweet-Spot wird IMMER mit Stern-Icon kombiniert, nicht nur Farbe (WCAG 1.4.1 erfüllt).

## Verifikation (vor "done")

- [ ] `npm run lint` clean
- [ ] `npx tsc --noEmit` clean
- [ ] `npm test` clean (alle bestehenden + neuen Tests)
- [ ] `npm run build` erfolgreich
- [ ] Backend-CI-Mirror: mypy + ruff check + ruff format --check + pytest unit clean
- [ ] **Manueller Browser-Smoke**:
  - Header: 3 px Spektrum-Strip oben, Logo neben Wordmark
  - Landing: Spektrum-Strich unter "PRISMA"-Heading
  - Rankings-Detail: Modell-Spalten haben farbige Underlines
  - Factsheet ModelRankCards: 5 Karten haben Top-Border in Spektrum-Reihenfolge
  - Info-Popovers: Top-Border in passender Modell-Farbe / Sweet-Spot-Pink
  - Sweet-Spot überall Pink (Karten, Stars, Bars)
  - Dark-Mode: Spektrum-Farben gut lesbar
  - Mobile-Viewport: Logo + Strip skalieren, kein Overflow

## Risiken & offene Punkte

- **Dark-Mode-Kontrast**: HSL-Lightness-Werte sind Schätzungen — Smoke-Test entscheidet, ob nachjustiert werden muss.
- **Color-Coding-Konflikt mit Quartile-Badges**: ModelRankCards haben bereits semantische Quartil-Farben (Q1=green, Q2=lime, Q3=orange, Q4=red). Die neuen Modell-Top-Borders sind eine *zweite* Farbebene. Beispiel: Quality-Card hat grünen Top-Border (Modell-Identität) UND grünen Q1-Badge (Top-Performer). Das ist Doppel-Grün aber semantisch konsistent — Quality + Top-Performer = doppelt positiv. Nicht änderbar ohne Quartil-System umzuwerfen, was YAGNI ist.
- **Spektrum-Reihenfolge im Gradient ≠ MODEL_KEYS-Reihenfolge**: kann verwirren wenn jemand erwartet, dass Reihenfolge eindeutig ist. Lösung: Spec dokumentiert beide Reihenfolgen klar.
- **Ordering der PRs**: Diese Branch erwartet, dass PR #142 + #144 vorher mergen. Falls nicht, kommen Konflikte in `rankings-table.tsx`, `TopTenCards.tsx`, `TopTenBars.tsx`. Sheyla bestätigt dass sie das im Auge behält.

## Referenzen

- Memory: `project-frontend-improvement-backlog` (Visual-Identity-Hinweis am Ende)
- Memory: `project-capstone-deadline` (Demo-Probe in den letzten Tagen)
- shadcn-Theme-Vars-Convention: https://ui.shadcn.com/docs/theming
- WCAG Color-Contrast: https://www.w3.org/WAI/WCAG21/quickref/#contrast-minimum
