# Visual-Identity-Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PRISMA-Spektrum-Metapher wird visuell sichtbar — 5 Modelle in Spektrum-Farben, Sweet-Spot wechselt von Amber zu Pink, Header bekommt Gradient-Strip + Custom-Logo, kleine Modell-Color-Akzente in ModelRankCards, Rankings-Tabelle und Info-Popovers.

**Architecture:** CSS-Vars + Tailwind-Tokens als Single Source of Truth, `MODEL_INFO` bekommt `colorVar`-Feld zur einfachen Konsumierung. Inline-Styles für dynamische Modell-Farben (Tailwind generiert keine dynamischen Klassen aus Runtime-Werten). Sweet-Spot-Migration ist Such-und-Ersetz über 5 Stellen.

**Tech Stack:** Next.js 14, React, Tailwind, shadcn HSL-Vars, lucide-react, Vitest + @testing-library/react.

**Spec:** `docs/specs/2026-05-23-visual-identity-polish-design.md`

**Prerequisite:** PRs #142 (Tooltips) und #144 (Top-10-Leaderboard) MÜSSEN vor Start dieser Implementation gemerged sein. Diese Branch wurde von main bei `446ea40` (vor den Merges) erstellt — nach Merge der beiden PRs muss diese Branch rebased werden:

```bash
git fetch origin
git rebase origin/main
```

Erst wenn `frontend/lib/model-info.ts`, `frontend/components/InfoPopover.tsx`, `frontend/components/ModelInfoIcon.tsx`, `frontend/components/rankings/TopTenCards.tsx`, `frontend/components/rankings/TopTenBars.tsx` existieren, kann der Plan ausgeführt werden.

---

## File Structure

**Neue Dateien:**
- `frontend/components/brand/PrismaLogo.tsx` — Custom SVG-Logo
- `frontend/components/brand/__tests__/PrismaLogo.test.tsx`

**Geänderte Dateien:**
- `frontend/app/globals.css` — neue CSS-Vars + `.bg-spectrum`-Utility
- `frontend/tailwind.config.ts` — `model.*` und `sweet-spot` Color-Tokens
- `frontend/lib/model-info.ts` — `colorVar` Feld in `MODEL_INFO`
- `frontend/lib/__tests__/model-info.test.ts` — Test für `colorVar`
- `frontend/app/layout.tsx` — Header bekommt Gradient-Strip + Logo
- `frontend/app/page.tsx` — Hero bekommt Spektrum-Strich unter `<h1>`
- `frontend/components/InfoPopover.tsx` — neues `topBorderColor`-Prop
- `frontend/components/__tests__/InfoPopover.test.tsx` — Test für Prop
- `frontend/components/ModelInfoIcon.tsx` — reicht Color durch
- `frontend/components/__tests__/ModelInfoIcon.test.tsx` — Test für Color-Pass-Through
- `frontend/components/factsheet/ModelRankCards.tsx` — Top-Border pro Karte
- `frontend/components/factsheet/__tests__/ModelRankCards.test.tsx` — Test für Top-Border
- `frontend/app/rankings/[runId]/rankings-table.tsx` — Spalten-Indikator + Sweet-Spot-Pink
- `frontend/app/rankings/__tests__/rankings-table.test.tsx` — Sweet-Spot-Pink Tests
- `frontend/components/rankings/TopTenCards.tsx` — Sweet-Spot Amber→Pink
- `frontend/components/rankings/__tests__/TopTenCards.test.tsx` — Tests umstellen
- `frontend/components/rankings/TopTenBars.tsx` — Sweet-Spot Amber→Pink
- `frontend/components/rankings/__tests__/TopTenBars.test.tsx` — Tests umstellen

---

### Task 1: Token-Foundation (CSS-Vars + Tailwind + MODEL_INFO)

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/lib/model-info.ts`
- Modify: `frontend/lib/__tests__/model-info.test.ts`

- [ ] **Step 1: Failing Test für colorVar schreiben**

In `frontend/lib/__tests__/model-info.test.ts`, in den existierenden `describe('MODEL_INFO', () => {`-Block diesen Test ergänzen:

```typescript
  it('hat eine colorVar pro Modell-Key (CSS-Custom-Property)', () => {
    const expected: Record<string, string> = {
      quality_classic: 'var(--model-quality)',
      alpha: 'var(--model-alpha)',
      trend_momentum: 'var(--model-trend)',
      value_alpha_potential: 'var(--model-value)',
      diversification: 'var(--model-diversification)',
    };
    for (const key of MODEL_KEYS) {
      expect(MODEL_INFO[key].colorVar).toBe(expected[key]);
    }
  });
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run lib/__tests__/model-info.test.ts
```

Expected: FAIL — neuer Test scheitert, `colorVar` existiert nicht.

- [ ] **Step 3: MODEL_INFO um colorVar erweitern**

In `frontend/lib/model-info.ts`, ändere den `MODEL_INFO`-Type und ergänze pro Eintrag das `colorVar`-Feld:

```typescript
export const MODEL_INFO: Record<ModelKey, { label: string; description: string; colorVar: string }> = {
  quality_classic: {
    label: 'Quality',
    description:
      'Fundamental gesund & günstig bewertet — Kombiniert 8 klassische Kennzahlen (Marge, Verschuldung, ROE, KGV …) zu einem Score.',
    colorVar: 'var(--model-quality)',
  },
  alpha: {
    label: 'Alpha',
    description:
      'Konsistent besser als der Index — Outperformance vs. Benchmark über mehrere Zeithorizonte, mit Sharpe gewichtet.',
    colorVar: 'var(--model-alpha)',
  },
  trend_momentum: {
    label: 'Trend',
    description:
      'Aktuelles Momentum — Welche Aktien zuletzt stärker als der Markt liefen, jüngere Daten zählen mehr.',
    colorVar: 'var(--model-trend)',
  },
  value_alpha_potential: {
    label: 'Value',
    description:
      'Mean-Reversion-Kandidaten — Wie weit unter dem eigenen historischen Outperformance-Hoch der Titel steht.',
    colorVar: 'var(--model-value)',
  },
  diversification: {
    label: 'Diversification',
    description:
      'Risiko-Diversifikatoren — Niedrige Eigenvolatilität und niedrige Korrelation zu anderen Titeln im Universum.',
    colorVar: 'var(--model-diversification)',
  },
};
```

- [ ] **Step 4: CSS-Vars in globals.css ergänzen**

In `frontend/app/globals.css`, im `:root`-Block (innerhalb `@layer base`) am Ende der Variable-Liste ergänzen:

```css
    /* Spektrum — 5 Modell-Farben */
    --model-quality:         142 71% 45%;
    --model-diversification: 217 91% 60%;
    --model-trend:           17 88% 48%;
    --model-value:           262 83% 58%;
    --model-alpha:           45 93% 47%;
    --sweet-spot:            330 81% 50%;
```

Im `.dark`-Block (Dark-Mode-Variante) ergänzen:

```css
    --model-quality:         142 71% 55%;
    --model-diversification: 217 91% 65%;
    --model-trend:           17 88% 58%;
    --model-value:           262 83% 68%;
    --model-alpha:           45 93% 57%;
    --sweet-spot:            330 81% 60%;
```

Am Ende der Datei (außerhalb `@layer base`) die Utility-Klasse ergänzen:

```css
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

- [ ] **Step 5: Tailwind-Token-Extension**

In `frontend/tailwind.config.ts`, im `theme.extend.colors`-Block (am Ende der `colors:` Map, vor dem schließenden `},`) ergänzen:

```typescript
        model: {
          quality: 'hsl(var(--model-quality))',
          diversification: 'hsl(var(--model-diversification))',
          trend: 'hsl(var(--model-trend))',
          value: 'hsl(var(--model-value))',
          alpha: 'hsl(var(--model-alpha))',
        },
        'sweet-spot': 'hsl(var(--sweet-spot))',
```

- [ ] **Step 6: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run lib/__tests__/model-info.test.ts && npx tsc --noEmit && npm run lint
```

Expected: alle MODEL_INFO-Tests grün (8 + 1 neu), tsc clean, lint clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts frontend/lib/model-info.ts frontend/lib/__tests__/model-info.test.ts
git commit -m "feat(frontend): Token-Foundation für Spektrum-Branding

CSS-Vars für 5 Modell-Farben + Sweet-Spot (Pink), Tailwind-Tokens
model.* und sweet-spot, .bg-spectrum Utility-Klasse, MODEL_INFO
bekommt colorVar pro Modell. Dark-Mode-Lightness leicht erhöht.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: PrismaLogo Komponente (TDD)

**Files:**
- Create: `frontend/components/brand/PrismaLogo.tsx`
- Test: `frontend/components/brand/__tests__/PrismaLogo.test.tsx`

- [ ] **Step 1: Failing Tests schreiben**

Erstelle `frontend/components/brand/__tests__/PrismaLogo.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';

import { PrismaLogo } from '../PrismaLogo';

describe('PrismaLogo', () => {
  it('rendert ein SVG-Element mit viewBox', () => {
    const { container } = render(<PrismaLogo />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('viewBox')).toBe('0 0 24 24');
  });

  it('enthält 5 stop-Elemente für die Spektrum-Farben', () => {
    const { container } = render(<PrismaLogo />);
    const stops = container.querySelectorAll('stop');
    expect(stops).toHaveLength(5);
    const colors = Array.from(stops).map((s) => s.getAttribute('stop-color'));
    expect(colors).toEqual(['#16a34a', '#2563eb', '#ea580c', '#7c3aed', '#eab308']);
  });

  it('reicht className-Prop an SVG durch', () => {
    const { container } = render(<PrismaLogo className="h-6 w-6" />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('class')).toMatch(/h-6 w-6/);
  });

  it('hat aria-label für Screenreader', () => {
    const { container } = render(<PrismaLogo />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('aria-label')).toBe('PRISMA Logo');
  });
});
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run components/brand/__tests__/PrismaLogo.test.tsx
```

Expected: FAIL — `Cannot find module '../PrismaLogo'`.

- [ ] **Step 3: Komponente implementieren**

Erstelle `frontend/components/brand/PrismaLogo.tsx`:

```tsx
interface Props {
  className?: string;
}

export function PrismaLogo({ className }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      aria-label="PRISMA Logo"
      role="img"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="prisma-spectrum" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#16a34a" />
          <stop offset="25%" stopColor="#2563eb" />
          <stop offset="50%" stopColor="#ea580c" />
          <stop offset="75%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#eab308" />
        </linearGradient>
      </defs>
      <path
        d="M4 20 L12 4 L20 20 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <line
        x1="14"
        y1="13"
        x2="22"
        y2="13"
        stroke="url(#prisma-spectrum)"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </svg>
  );
}
```

- [ ] **Step 4: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run components/brand/__tests__/PrismaLogo.test.tsx
```

Expected: PASS, 4 Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/brand/PrismaLogo.tsx frontend/components/brand/__tests__/PrismaLogo.test.tsx
git commit -m "feat(frontend): PrismaLogo Komponente

Custom SVG mit Prisma-Dreieck und Spektrum-Strich.
5 Spektrum-Stops, aria-label, className-Pass-Through.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Header + Landing-Hero (Brand-Moments)

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Layout — Spektrum-Strip + Logo**

In `frontend/app/layout.tsx`, oben die Logo-Import ergänzen (nach den anderen `@/`-Imports):

```typescript
import { PrismaLogo } from '@/components/brand/PrismaLogo';
```

Im `<body>`-Block, direkt nach `<Providers>` und vor `<header>` den 3-px-Strip einfügen (über die ganze Breite):

```tsx
        <Providers>
          <div className="h-[3px] bg-spectrum" aria-hidden="true" />
          <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
```

Im Header-Container das Logo VOR dem Wordmark "PRISMA" einsetzen — `<Link>` wrapper bekommt Logo + Span:

```tsx
              <Link
                href="/"
                className="mr-8 flex items-center gap-2 font-bold tracking-tight text-foreground"
              >
                <PrismaLogo className="h-6 w-6" />
                <span className="text-lg font-black uppercase tracking-widest">PRISMA</span>
              </Link>
```

- [ ] **Step 2: Landing-Hero — Spektrum-Strich**

In `frontend/app/page.tsx`, im Hero-Block (Suche nach `<h1 className="text-4xl font-black tracking-tight sm:text-5xl">PRISMA</h1>`) direkt nach dem `<h1>` einen 4-px-Spektrum-Strich einfügen:

```tsx
        <div className="space-y-2">
          <h1 className="text-4xl font-black tracking-tight sm:text-5xl">PRISMA</h1>
          <div className="h-1 w-[200px] rounded-full bg-spectrum" aria-hidden="true" />
          <p className="max-w-2xl text-lg text-muted-foreground">
            Quantitative Stock-Selection zerlegt in analytische Dimensionen
          </p>
        </div>
```

- [ ] **Step 3: Verifikation**

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm test
```

Expected: alles grün. Bestehende Tests dürfen nicht brechen.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/page.tsx
git commit -m "feat(frontend): Header-Branding und Landing-Hero-Strich

3 px Spektrum-Strip über dem Header, PrismaLogo neben dem Wordmark.
Landing-Hero bekommt 200×4 px Spektrum-Strich unter dem H1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: InfoPopover topBorderColor Prop + ModelInfoIcon Color-Pass-Through (TDD)

**Files:**
- Modify: `frontend/components/InfoPopover.tsx`
- Modify: `frontend/components/__tests__/InfoPopover.test.tsx`
- Modify: `frontend/components/ModelInfoIcon.tsx`
- Modify: `frontend/components/__tests__/ModelInfoIcon.test.tsx`

- [ ] **Step 1: Failing Tests schreiben**

In `frontend/components/__tests__/InfoPopover.test.tsx`, im `describe('InfoPopover', () => {`-Block ergänzen (vor dem schließenden `})`):

```typescript
  it('rendert Top-Border bei topBorderColor-Prop', () => {
    render(
      <InfoPopover ariaLabel="Info" topBorderColor="hsl(var(--model-quality))">
        <p>Content</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    const content = screen.getByText('Content').parentElement;
    expect(content?.style.borderTopWidth).toBe('4px');
    expect(content?.style.borderTopColor).toBe('hsl(var(--model-quality))');
  });

  it('kein Top-Border ohne topBorderColor', () => {
    render(
      <InfoPopover ariaLabel="Info">
        <p>Content</p>
      </InfoPopover>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    const content = screen.getByText('Content').parentElement;
    expect(content?.style.borderTopWidth).toBeFalsy();
  });
```

In `frontend/components/__tests__/ModelInfoIcon.test.tsx`, im `describe('ModelInfoIcon', () => {`-Block ergänzen:

```typescript
  it('reicht passende colorVar als topBorderColor an InfoPopover', () => {
    render(<ModelInfoIcon modelKey="quality_classic" />);
    fireEvent.click(screen.getByRole('button', { name: 'Info zu Quality' }));
    const content = screen.getByText(/8 klassische Kennzahlen/).parentElement;
    expect(content?.style.borderTopColor).toBe('hsl(var(--model-quality))');
  });
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run components/__tests__/InfoPopover.test.tsx components/__tests__/ModelInfoIcon.test.tsx
```

Expected: FAIL — neue Tests scheitern, weil `topBorderColor` noch nicht implementiert.

- [ ] **Step 3: InfoPopover anpassen**

In `frontend/components/InfoPopover.tsx`:

```tsx
'use client';

import { Info } from 'lucide-react';
import type { CSSProperties, ReactNode } from 'react';

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface Props {
  ariaLabel: string;
  children: ReactNode;
  topBorderColor?: string;
}

export function InfoPopover({ ariaLabel, children, topBorderColor }: Props) {
  const contentStyle: CSSProperties | undefined = topBorderColor
    ? { borderTopColor: topBorderColor, borderTopWidth: 4 }
    : undefined;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={ariaLabel}
          onClick={(e) => e.stopPropagation()}
          className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground opacity-60 hover:opacity-100 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="max-w-xs text-sm leading-relaxed"
        side="top"
        style={contentStyle}
      >
        {children}
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 4: ModelInfoIcon anpassen**

In `frontend/components/ModelInfoIcon.tsx`:

```tsx
import { InfoPopover } from './InfoPopover';
import { MODEL_INFO, type ModelKey } from '@/lib/model-info';

interface Props {
  modelKey: ModelKey;
}

export function ModelInfoIcon({ modelKey }: Props) {
  const info = MODEL_INFO[modelKey];
  return (
    <InfoPopover ariaLabel={`Info zu ${info.label}`} topBorderColor={`hsl(${info.colorVar})`}>
      <p>{info.description}</p>
    </InfoPopover>
  );
}
```

- [ ] **Step 5: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run components/__tests__/InfoPopover.test.tsx components/__tests__/ModelInfoIcon.test.tsx
```

Expected: PASS — alle bisherigen + neuen Tests grün.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/InfoPopover.tsx frontend/components/ModelInfoIcon.tsx frontend/components/__tests__/InfoPopover.test.tsx frontend/components/__tests__/ModelInfoIcon.test.tsx
git commit -m "feat(frontend): InfoPopover topBorderColor + ModelInfoIcon Pass-Through

Popover-Content bekommt optional 4 px farbigen Top-Border.
ModelInfoIcon reicht die Modell-Farbe automatisch durch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: ModelRankCards Top-Border (TDD)

**Files:**
- Modify: `frontend/components/factsheet/ModelRankCards.tsx`
- Modify: `frontend/components/factsheet/__tests__/ModelRankCards.test.tsx`

- [ ] **Step 1: Failing Tests schreiben**

In `frontend/components/factsheet/__tests__/ModelRankCards.test.tsx`, im `describe('ModelRankCards', () => {`-Block ergänzen:

```typescript
  it('jede Card hat border-t-4 und Modell-spezifische borderTopColor', () => {
    const { container } = render(<ModelRankCards perModelRanks={perModelRanks} />);
    const cards = container.querySelectorAll<HTMLElement>('[data-model-key]');
    expect(cards).toHaveLength(5);

    const colorByKey: Record<string, string> = {
      quality_classic: 'hsl(var(--model-quality))',
      alpha: 'hsl(var(--model-alpha))',
      trend_momentum: 'hsl(var(--model-trend))',
      value_alpha_potential: 'hsl(var(--model-value))',
      diversification: 'hsl(var(--model-diversification))',
    };
    for (const card of Array.from(cards)) {
      const key = card.dataset.modelKey!;
      expect(card.className).toMatch(/border-t-4/);
      expect(card.style.borderTopColor).toBe(colorByKey[key]);
    }
  });
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run components/factsheet/__tests__/ModelRankCards.test.tsx
```

Expected: FAIL — neuer Test scheitert.

- [ ] **Step 3: Komponente anpassen**

In `frontend/components/factsheet/ModelRankCards.tsx`, den `<Card>`-Block innerhalb der `.map(...)` ergänzen. Suche:

```tsx
        return (
          <Card key={key}>
```

Ersetze durch:

```tsx
        const info = MODEL_INFO[key];
        return (
          <Card
            key={key}
            data-model-key={key}
            className="border-t-4"
            style={{ borderTopColor: `hsl(${info.colorVar})` }}
          >
```

- [ ] **Step 4: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run components/factsheet/__tests__/ModelRankCards.test.tsx
```

Expected: PASS — alle bisherigen + neuen Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/factsheet/ModelRankCards.tsx frontend/components/factsheet/__tests__/ModelRankCards.test.tsx
git commit -m "feat(frontend): ModelRankCards Spektrum-Top-Border

Jede der 5 Modell-Karten bekommt 4 px Top-Border in der passenden
Spektrum-Farbe. Spektrum auf einen Blick erkennbar.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: RankingsTable Header-Indikator + Sweet-Spot Pink-Migration (TDD)

**Files:**
- Modify: `frontend/app/rankings/[runId]/rankings-table.tsx`
- Modify: `frontend/app/rankings/__tests__/rankings-table.test.tsx`

- [ ] **Step 1: Failing Tests schreiben**

In `frontend/app/rankings/__tests__/rankings-table.test.tsx`, im `describe('RankingsTable', () => {`-Block ergänzen:

```typescript
  it('Quality-Header hat box-shadow mit Modell-Quality-Farbe', () => {
    const { container } = render(<RankingsTable items={sampleItems} runId="test-run-id" />);
    const qualityHead = container.querySelector<HTMLElement>('[data-model-key="quality_classic"]');
    expect(qualityHead).not.toBeNull();
    expect(qualityHead?.style.boxShadow).toContain('var(--model-quality)');
  });

  it('SweetSpotBadge nutzt Pink-Klassen', () => {
    render(<RankingsTable items={sampleItems} runId="test-run-id" />);
    const badge = screen.getByRole('button', { name: 'Sweet-Spot-Begründung für AAPL' });
    // Button selbst hat keine Pink-Klasse, aber das Star-Icon im Popover/Cell ist Pink.
    // Wir prüfen indirekt: Sweet-Spot-Definition-Popover-Top-Border ist Pink.
    const definitionTrigger = screen.getByRole('button', { name: 'Sweet-Spot-Definition' });
    fireEvent.click(definitionTrigger);
    const content = screen.getByText(/Top-25 ?% in mindestens 3 von 5/).parentElement;
    expect(content?.style.borderTopColor).toBe('hsl(var(--sweet-spot))');
  });
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run app/rankings/__tests__/rankings-table.test.tsx
```

Expected: FAIL — Header-Indikator und Pink-Sweet-Spot fehlen.

- [ ] **Step 3: Komponente anpassen**

In `frontend/app/rankings/[runId]/rankings-table.tsx`:

**a) `SortableHead` Props erweitern um optionales `indicatorColor`**. Ersetze die `SortableHeadProps`-Interface und Funktion:

```tsx
interface SortableHeadProps {
  sortKey: SortKey;
  activeSortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  infoIcon?: React.ReactNode;
  indicatorColor?: string;
  modelKey?: string;
  children: React.ReactNode;
}

function SortableHead({
  sortKey,
  activeSortKey,
  sortDir,
  onSort,
  infoIcon,
  indicatorColor,
  modelKey,
  children,
}: SortableHeadProps) {
  const isActive = activeSortKey === sortKey;
  const ariaSort = isActive ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
  const Icon = isActive ? (sortDir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
  const style = indicatorColor
    ? { boxShadow: `inset 0 -4px 0 ${indicatorColor}` }
    : undefined;

  return (
    <TableHead
      className="cursor-pointer select-none"
      onClick={() => onSort(sortKey)}
      aria-sort={ariaSort}
      data-model-key={modelKey}
      style={style}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {infoIcon}
        <Icon className={`h-3 w-3 ${isActive ? '' : 'opacity-30'}`} />
      </span>
    </TableHead>
  );
}
```

**b) MODEL_COLUMNS-Map: `indicatorColor` durchreichen**. Suche:

```tsx
              {MODEL_COLUMNS.map((col) => (
                <SortableHead
                  key={col.key}
                  sortKey={col.key}
                  activeSortKey={sortKey}
                  sortDir={sortDir}
                  onSort={handleSort}
                  infoIcon={<ModelInfoIcon modelKey={col.key} />}
                >
                  {col.label}
                </SortableHead>
              ))}
```

Ersetze durch:

```tsx
              {MODEL_COLUMNS.map((col) => (
                <SortableHead
                  key={col.key}
                  sortKey={col.key}
                  activeSortKey={sortKey}
                  sortDir={sortDir}
                  onSort={handleSort}
                  infoIcon={<ModelInfoIcon modelKey={col.key} />}
                  indicatorColor={`hsl(${MODEL_INFO[col.key].colorVar})`}
                  modelKey={col.key}
                >
                  {col.label}
                </SortableHead>
              ))}
```

**c) Sweet-Spot-Definition-InfoPopover bekommt Pink-Top-Border**. Suche:

```tsx
              <TableHead>
                <span className="inline-flex items-center gap-1">
                  Sweet-Spot
                  <InfoPopover ariaLabel="Sweet-Spot-Definition">
                    <p>{SWEET_SPOT_DEFINITION}</p>
                  </InfoPopover>
                </span>
              </TableHead>
```

Ersetze durch:

```tsx
              <TableHead>
                <span className="inline-flex items-center gap-1">
                  Sweet-Spot
                  <InfoPopover
                    ariaLabel="Sweet-Spot-Definition"
                    topBorderColor="hsl(var(--sweet-spot))"
                  >
                    <p>{SWEET_SPOT_DEFINITION}</p>
                  </InfoPopover>
                </span>
              </TableHead>
```

**d) SweetSpotBadge bekommt Pink-Top-Border**. Suche die Funktion:

```tsx
function SweetSpotBadge({
  ticker,
  perModelRanks,
  totalStocks,
}: {
  ticker: string;
  perModelRanks: Record<string, number | null>;
  totalStocks: number;
}) {
  const sweetSpotKeys = getSweetSpotModels(perModelRanks, totalStocks);
  const labels = sweetSpotKeys.map((k) => MODEL_INFO[k].label).join(', ');
  const count = sweetSpotKeys.length;

  return (
    <InfoPopover ariaLabel={`Sweet-Spot-Begründung für ${ticker}`}>
      <p>
        <strong>{ticker}</strong> ist Top-25 % in {labels} ({count}/5 Modellen).
      </p>
    </InfoPopover>
  );
}
```

Ersetze durch:

```tsx
function SweetSpotBadge({
  ticker,
  perModelRanks,
  totalStocks,
}: {
  ticker: string;
  perModelRanks: Record<string, number | null>;
  totalStocks: number;
}) {
  const sweetSpotKeys = getSweetSpotModels(perModelRanks, totalStocks);
  const labels = sweetSpotKeys.map((k) => MODEL_INFO[k].label).join(', ');
  const count = sweetSpotKeys.length;

  return (
    <InfoPopover
      ariaLabel={`Sweet-Spot-Begründung für ${ticker}`}
      topBorderColor="hsl(var(--sweet-spot))"
    >
      <p>
        <strong>{ticker}</strong> ist Top-25 % in {labels} ({count}/5 Modellen).
      </p>
    </InfoPopover>
  );
}
```

- [ ] **Step 4: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run app/rankings/__tests__/rankings-table.test.tsx
```

Expected: PASS — alle bisherigen + neuen Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/rankings/[runId]/rankings-table.tsx frontend/app/rankings/__tests__/rankings-table.test.tsx
git commit -m "feat(frontend): RankingsTable Spektrum-Indikator + Sweet-Spot Pink

Modell-Spalten bekommen box-shadow Underline in Spektrum-Farbe.
Sweet-Spot-Popover-Top-Border in Pink (#db2777, außerhalb Spektrum).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: TopTenCards Sweet-Spot-Pink-Migration (TDD)

**Files:**
- Modify: `frontend/components/rankings/TopTenCards.tsx`
- Modify: `frontend/components/rankings/__tests__/TopTenCards.test.tsx`

- [ ] **Step 1: Tests umstellen**

In `frontend/components/rankings/__tests__/TopTenCards.test.tsx`, suche:

```typescript
  it('Sweet-Spot-Karten haben Amber-Border-Klasse', () => {
    render(<TopTenCards items={items} runId="run-1" />);
    const aaplLink = screen.getByText('AAPL').closest('a');
    expect(aaplLink?.className).toMatch(/border-amber-400/);
    const nvdaLink = screen.getByText('NVDA').closest('a');
    expect(nvdaLink?.className).not.toMatch(/border-amber-400/);
  });
```

Ersetze durch:

```typescript
  it('Sweet-Spot-Karten haben Pink-Border-Klasse', () => {
    render(<TopTenCards items={items} runId="run-1" />);
    const aaplLink = screen.getByText('AAPL').closest('a');
    expect(aaplLink?.className).toMatch(/border-pink-500/);
    const nvdaLink = screen.getByText('NVDA').closest('a');
    expect(nvdaLink?.className).not.toMatch(/border-pink-500/);
  });
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run components/rankings/__tests__/TopTenCards.test.tsx
```

Expected: FAIL — Pink-Klasse noch nicht im Code.

- [ ] **Step 3: Komponente migrieren**

In `frontend/components/rankings/TopTenCards.tsx`, suche:

```tsx
        const sweetSpotClasses = item.is_sweet_spot
          ? 'border-amber-400 bg-amber-50/60 dark:border-amber-500 dark:bg-amber-950/30'
          : 'border-border bg-card';
```

Ersetze durch:

```tsx
        const sweetSpotClasses = item.is_sweet_spot
          ? 'border-pink-500 bg-pink-50/60 dark:border-pink-600 dark:bg-pink-950/30'
          : 'border-border bg-card';
```

Im selben File, suche das Star-Icon:

```tsx
              {item.is_sweet_spot && (
                <Star
                  className="h-3.5 w-3.5 fill-amber-400 text-amber-400"
                  aria-label="Sweet-Spot"
                />
              )}
```

Ersetze durch:

```tsx
              {item.is_sweet_spot && (
                <Star
                  className="h-3.5 w-3.5 fill-pink-600 text-pink-600"
                  aria-label="Sweet-Spot"
                />
              )}
```

- [ ] **Step 4: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run components/rankings/__tests__/TopTenCards.test.tsx
```

Expected: PASS, 5 Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/rankings/TopTenCards.tsx frontend/components/rankings/__tests__/TopTenCards.test.tsx
git commit -m "fix(frontend): TopTenCards Sweet-Spot Amber→Pink

Pink ist semantisch korrekt: Sweet-Spot ist außerhalb des
5-Modelle-Spektrums (Meta-Auszeichnung über mehrere Dimensionen).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: TopTenBars Sweet-Spot-Pink-Migration (TDD)

**Files:**
- Modify: `frontend/components/rankings/TopTenBars.tsx`
- Modify: `frontend/components/rankings/__tests__/TopTenBars.test.tsx`

- [ ] **Step 1: Tests umstellen**

In `frontend/components/rankings/__tests__/TopTenBars.test.tsx`, suche die Sweet-Spot-Fill-Assertion:

```typescript
    const amberCount = fills.filter((f) => f === '#f59e0b').length;
    expect(amberCount).toBe(2);
```

Ersetze durch:

```typescript
    const pinkCount = fills.filter((f) => f === '#db2777').length;
    expect(pinkCount).toBe(2);
```

- [ ] **Step 2: Tests laufen lassen, müssen fehlen**

```bash
cd frontend && npx vitest run components/rankings/__tests__/TopTenBars.test.tsx
```

Expected: FAIL — Bars sind noch Amber.

- [ ] **Step 3: Komponente migrieren**

In `frontend/components/rankings/TopTenBars.tsx`, suche die Konstante:

```typescript
const AMBER = '#f59e0b';
const PRIMARY = 'hsl(var(--primary))';
```

Ersetze durch:

```typescript
const SWEET_SPOT = '#db2777';
const PRIMARY = 'hsl(var(--primary))';
```

Im selben File alle Vorkommen von `AMBER` durch `SWEET_SPOT` ersetzen (im `TickLabel` und im `Cell.fill`). Beispiele:

```tsx
  const fill = datum?.is_sweet_spot ? SWEET_SPOT : 'currentColor';
```

```tsx
            <Cell key={entry.ticker} fill={entry.is_sweet_spot ? SWEET_SPOT : PRIMARY} />
```

Im CustomTooltip, suche:

```tsx
      {is_sweet_spot && <span className="text-amber-500"> • Sweet-Spot</span>}
```

Ersetze durch:

```tsx
      {is_sweet_spot && <span className="text-pink-600"> • Sweet-Spot</span>}
```

- [ ] **Step 4: Tests laufen lassen, müssen grün sein**

```bash
cd frontend && npx vitest run components/rankings/__tests__/TopTenBars.test.tsx
```

Expected: PASS, 4 Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/rankings/TopTenBars.tsx frontend/components/rankings/__tests__/TopTenBars.test.tsx
git commit -m "fix(frontend): TopTenBars Sweet-Spot Amber→Pink

Konstante AMBER → SWEET_SPOT (#db2777), Tick-Text-Color und
Tooltip-Highlight ebenfalls auf Pink umgestellt.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Pre-Push-Mirror + Manual Smoke

**Files:** keine — Validation-Schritt.

- [ ] **Step 1: Frontend Lint + Typecheck + Tests**

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm test
```

Expected: alles grün. Bei Fail: fixen und neu committen.

- [ ] **Step 2: Frontend Production Build**

```bash
cd frontend && npm run build
```

Expected: erfolgreich. Bundle-Sizes sollten kaum wachsen (nur SVG-Logo + 6 CSS-Vars).

- [ ] **Step 3: Backend Pre-Push-Mirror**

```bash
cd backend && uv run mypy . && uv run ruff check . && uv run ruff format --check . && uv run pytest tests/unit -q
```

Expected: grün. Backend unverändert.

- [ ] **Step 4: Dev-Server Manual-Smoke**

```bash
cd frontend && npm run dev
```

Öffne `http://localhost:3000` und prüfe:

1. **Header**:
   - 3 px Spektrum-Strip ganz oben (kalt links → warm rechts)
   - Prisma-Logo neben "PRISMA"-Wordmark im Header-Container
2. **Landing-Hero** (`/`):
   - Unter `<h1>PRISMA</h1>` ein 200×4 px Spektrum-Strich (rounded-full)
3. **Rankings-Detail-Page** (`/rankings/{any completed runId}`):
   - 5 Modell-Spalten im Tabellen-Header haben farbige Underlines in Spektrum-Reihenfolge ihrer eigenen Definition
   - Klick auf Info-Icon im Quality-Header → Popover mit grüner Top-Border
   - Klick auf Info-Icon im Sweet-Spot-Header → Popover mit Pink-Top-Border
   - Sweet-Spot-Badge in einer Zeile → Klick → Pink-Top-Border, Ticker + Modell-Liste sichtbar
4. **Top-10-Sektion**:
   - Sweet-Spot-Karten haben Pink-Border + Pink-Stern (nicht mehr Amber)
   - Sweet-Spot-Bars sind Pink (nicht mehr Amber)
   - Y-Tick-Labels der Sweet-Spot-Tickers sind Pink
5. **Factsheet-Page** (`/rankings/{runId}/stock/{ticker}`):
   - 5 ModelRankCards haben Top-Border in passender Spektrum-Farbe
   - Klick auf Info-Icon in jeder Card → Popover mit passender Modell-Color als Top-Border
6. **Dark-Mode** (System-Theme toggeln):
   - Spektrum-Farben gut lesbar, kein Kontrast-Problem
   - Sweet-Spot Pink bleibt erkennbar
7. **Mobile-Viewport** (DevTools-Toggle 375 px):
   - Header-Logo skaliert, kein Overflow
   - Spektrum-Strich auf Landing rückt zentriert, bleibt 200 px

Dev-Server stoppen.

- [ ] **Step 5: Push + PR (nach Sheylas Freigabe)**

```bash
git push -u origin feat/visual-identity-polish
gh pr create --title "feat(frontend): Visual-Identity-Polish — PRISMA-Spektrum sichtbar" --body "…"
```

---

## Self-Review

- **Spec-Coverage:**
  - Farbpalette (5 Modell-Farben + Sweet-Spot) → Task 1 ✓
  - Spektrum-Gradient-Reihenfolge → Task 1 (`.bg-spectrum`) ✓
  - PrismaLogo Custom-SVG → Task 2 ✓
  - Header Gradient-Strip + Logo → Task 3 ✓
  - Landing-Hero Spektrum-Strich → Task 3 ✓
  - InfoPopover topBorderColor + ModelInfoIcon Pass-Through → Task 4 ✓
  - ModelRankCards Top-Border → Task 5 ✓
  - RankingsTable Spalten-Indikator → Task 6 ✓
  - Sweet-Spot Amber→Pink in rankings-table + TopTenCards + TopTenBars → Tasks 6, 7, 8 ✓
  - Dark-Mode Lightness-Werte → Task 1 (`.dark` Block) ✓
  - Manueller Smoke incl. Dark-Mode + Mobile → Task 9 ✓

- **Placeholder-Scan:** Keine TBDs, alle Code-Blöcke vollständig.

- **Type-Konsistenz:**
  - `MODEL_INFO[key].colorVar: string` konsistent in Task 1 (Definition) + Tasks 4/5/6 (Konsumierung).
  - `InfoPopover topBorderColor?: string` konsistent in Task 4 (Definition) + Tasks 5/6 (Konsumierung).
  - `SortableHead indicatorColor?: string` + `modelKey?: string` konsistent in Task 6.
  - `SWEET_SPOT` Konstante in TopTenBars (Task 8) ersetzt vorherige `AMBER`-Konstante vollständig.
  - Tailwind-Klassen `border-pink-500`, `fill-pink-600`, `text-pink-600` konsistent in Tasks 6/7/8.

Plan ist intern stimmig und vollständig.
