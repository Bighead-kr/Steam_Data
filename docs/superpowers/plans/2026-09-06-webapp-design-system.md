# 웹앱 디자인 시스템 & UI 재구축 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `web/` (the Steam Hidden Gems Next.js app) on a real design system — dark, minimal, "hidden gem" themed — with a quadrant scatter chart, a detail modal, and a methodology page, so a portfolio reviewer understands the product's value in under a minute.

**Architecture:** Frontend-only work. No backend changes — `GET /games/gems` already returns every field the UI needs. Introduce Tailwind CSS v4 (CSS-first `@theme` tokens, no `tailwind.config.ts`) and a self-hosted Pretendard font, extract pure helper functions (`lib/percentile.ts`, `lib/filterQuery.ts`) that carry the business logic so components stay thin and testable, build each UI piece bottom-up (badge → card → panel → chart → modal), then wire them together in `app/page.tsx` with URL-query-string state. Add a static `/about` page for methodology.

**Tech Stack:** Next.js 14.2.35 (App Router, existing), Tailwind CSS 4.3.3 (`@tailwindcss/postcss` + `postcss` 8.5.28), Pretendard 1.3.9 (npm package, self-hosted, no external CDN), Vitest 2.1.9 + Testing Library (existing).

**Spec:** [docs/superpowers/specs/2026-09-06-webapp-design-system-design.md](../specs/2026-09-06-webapp-design-system-design.md)

## Global Constraints

- Dark theme only — no light-mode variant (spec: "다크 전용, 라이트 모드 없음").
- Color tokens exactly as specified: `--color-bg-void: #12141a`, `--color-surface: #1b1e27`, `--color-surface-raised: #242835`, `--color-border: #2e3340`, `--color-ink-primary: #edeef2`, `--color-ink-secondary: #9ba0af`, `--color-ink-muted: #6a6f7e`, `--color-accent-gem: #7c6af0`.
- `accent-gem` is used only for the hidden-gem zone, its badge, and primary CTAs — no other use.
- Single font family: Pretendard, self-hosted via the `pretendard` npm package — no second typeface, no external font CDN.
- No chart library — the scatter chart is hand-built SVG per the dataviz mark specs already chosen in the design doc (thin marks, hover layer, table-view accessibility fallback).
- No new backend endpoints or schema changes. All data comes from the existing `GET /games/gems`.
- Filter state lives in the URL query string (back/forward and share-by-link must work).
- Hidden-gem zone threshold: `quality_pctile >= 0.7 && exposure_pctile <= 0.3` (inclusive on both bounds).

---

### Task 1: Design tokens — Tailwind v4 + Pretendard font pipeline

**Files:**
- Modify: `web/package.json`
- Create: `web/postcss.config.mjs`
- Create: `web/app/globals.css`
- Modify: `web/app/layout.tsx`
- Test: `web/app/globals.test.ts`
- Test: `web/app/layout.test.ts`

**Interfaces:**
- Produces: CSS custom properties `--color-bg-void`, `--color-surface`, `--color-surface-raised`, `--color-border`, `--color-ink-primary`, `--color-ink-secondary`, `--color-ink-muted`, `--color-accent-gem`, `--font-sans`, consumed as Tailwind utility classes (`bg-bg-void`, `text-ink-primary`, `border-border`, `bg-accent-gem`, etc.) by every component task below.

- [ ] **Step 1: Add the new dependencies to `web/package.json`**

Edit the `dependencies` object to add:

```json
"pretendard": "1.3.9"
```

Edit the `devDependencies` object to add:

```json
"@tailwindcss/postcss": "4.3.3",
"postcss": "8.5.28",
"tailwindcss": "4.3.3"
```

- [ ] **Step 2: Install**

Run: `cd web && npm install`
Expected: lockfile updates, no errors.

- [ ] **Step 3: Write the failing tests**

Create `web/app/globals.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("./globals.css", import.meta.url), "utf-8");

describe("design tokens", () => {
  it("loads Pretendard before Tailwind so the font is available to every utility", () => {
    const pretendardIndex = css.indexOf('@import "pretendard');
    const tailwindIndex = css.indexOf('@import "tailwindcss"');
    expect(pretendardIndex).toBeGreaterThanOrEqual(0);
    expect(tailwindIndex).toBeGreaterThan(pretendardIndex);
  });

  it("defines the accent-gem token used by ScoreBadge and the scatter chart", () => {
    expect(css).toContain("--color-accent-gem: #7c6af0");
  });

  it("defines the void background and primary ink tokens", () => {
    expect(css).toContain("--color-bg-void: #12141a");
    expect(css).toContain("--color-ink-primary: #edeef2");
  });

  it("sets Pretendard as the sans font stack", () => {
    expect(css).toContain('--font-sans: "Pretendard"');
  });
});
```

Create `web/app/layout.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./layout.tsx", import.meta.url), "utf-8");

describe("RootLayout", () => {
  it("imports the global stylesheet so Tailwind utilities and tokens are available", () => {
    expect(source).toContain('import "./globals.css"');
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd web && npm test -- globals.test.ts layout.test.ts`
Expected: FAIL — `globals.css` does not exist yet (`ENOENT`) and `layout.tsx` doesn't import it.

- [ ] **Step 5: Create `web/postcss.config.mjs`**

```js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

- [ ] **Step 6: Create `web/app/globals.css`**

```css
@import "pretendard/dist/web/static/pretendard.css";
@import "tailwindcss";

@theme {
  --color-bg-void: #12141a;
  --color-surface: #1b1e27;
  --color-surface-raised: #242835;
  --color-border: #2e3340;
  --color-ink-primary: #edeef2;
  --color-ink-secondary: #9ba0af;
  --color-ink-muted: #6a6f7e;
  --color-accent-gem: #7c6af0;
  --font-sans: "Pretendard", ui-sans-serif, system-ui, sans-serif;
}

body {
  background-color: var(--color-bg-void);
  color: var(--color-ink-primary);
  font-family: var(--font-sans);
}
```

- [ ] **Step 7: Modify `web/app/layout.tsx`**

```tsx
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd web && npm test -- globals.test.ts layout.test.ts`
Expected: PASS (both files, 5 assertions total).

- [ ] **Step 9: Commit**

```bash
git add web/package.json web/package-lock.json web/postcss.config.mjs web/app/globals.css web/app/layout.tsx web/app/globals.test.ts web/app/layout.test.ts
git commit -m "feat(web): add Tailwind v4 design tokens and self-hosted Pretendard font"
```

---

### Task 2: Shared types & percentile helpers

**Files:**
- Create: `web/lib/types.ts`
- Create: `web/lib/percentile.ts`
- Test: `web/lib/percentile.test.ts`

**Interfaces:**
- Produces: `type Gem` (fields: `app_id: number`, `name: string`, `price_cents: number | null`, `genres: string[]`, `tags: string[]`, `review_score_pct: number | null`, `review_count: number | null`, `owners_low: number | null`, `owners_high: number | null`, `quality_pctile: number`, `exposure_pctile: number`, `hidden_gem_score: number`); `type Filters` (`genre: string`, `tag: string`, `maxPrice: string`); `topPercentileLabel(pctile: number): number`; `bottomPercentileLabel(pctile: number): number`; `isHiddenGemZone(qualityPctile: number, exposurePctile: number): boolean`. Every later task imports these from `web/lib/types` and `web/lib/percentile`.

- [ ] **Step 1: Write the failing test**

Create `web/lib/percentile.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { bottomPercentileLabel, isHiddenGemZone, topPercentileLabel } from "./percentile";

describe("topPercentileLabel", () => {
  it("floors at 1% instead of showing 0% for the top-ranked game", () => {
    expect(topPercentileLabel(1.0)).toBe(1);
  });

  it("rounds to the nearest percent", () => {
    expect(topPercentileLabel(0.9)).toBe(10);
  });
});

describe("bottomPercentileLabel", () => {
  it("rounds to the nearest percent", () => {
    expect(bottomPercentileLabel(0.2)).toBe(20);
  });
});

describe("isHiddenGemZone", () => {
  it("is true for high quality and low exposure", () => {
    expect(isHiddenGemZone(0.9, 0.1)).toBe(true);
  });

  it("is false for high quality and high exposure", () => {
    expect(isHiddenGemZone(0.9, 0.8)).toBe(false);
  });

  it("is false for low quality and low exposure", () => {
    expect(isHiddenGemZone(0.4, 0.1)).toBe(false);
  });

  it("treats both thresholds as inclusive", () => {
    expect(isHiddenGemZone(0.7, 0.3)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- percentile.test.ts`
Expected: FAIL — `./percentile` module not found.

- [ ] **Step 3: Create `web/lib/types.ts`**

```ts
export type Gem = {
  app_id: number;
  name: string;
  price_cents: number | null;
  genres: string[];
  tags: string[];
  review_score_pct: number | null;
  review_count: number | null;
  owners_low: number | null;
  owners_high: number | null;
  quality_pctile: number;
  exposure_pctile: number;
  hidden_gem_score: number;
};

export type Filters = {
  genre: string;
  tag: string;
  maxPrice: string;
};
```

- [ ] **Step 4: Create `web/lib/percentile.ts`**

```ts
// percentile_rank is inclusive-of-self, so the #1 ranked game in any
// cohort always has quality_pctile === 1.0; without the floor that would
// render as "상위 0%" for the single most important result.
export function topPercentileLabel(pctile: number): number {
  return Math.max(1, Math.round((1 - pctile) * 100));
}

export function bottomPercentileLabel(pctile: number): number {
  return Math.round(pctile * 100);
}

export const GEM_ZONE_MIN_QUALITY_PCTILE = 0.7;
export const GEM_ZONE_MAX_EXPOSURE_PCTILE = 0.3;

export function isHiddenGemZone(qualityPctile: number, exposurePctile: number): boolean {
  return (
    qualityPctile >= GEM_ZONE_MIN_QUALITY_PCTILE &&
    exposurePctile <= GEM_ZONE_MAX_EXPOSURE_PCTILE
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd web && npm test -- percentile.test.ts`
Expected: PASS (7 assertions).

- [ ] **Step 6: Commit**

```bash
git add web/lib/types.ts web/lib/percentile.ts web/lib/percentile.test.ts
git commit -m "feat(web): extract Gem/Filters types and percentile helpers"
```

---

### Task 3: `ScoreBadge` component

**Files:**
- Create: `web/components/ScoreBadge.tsx`
- Test: `web/components/ScoreBadge.test.tsx`

**Interfaces:**
- Consumes: nothing from earlier tasks (no data dependency, just a presentational component).
- Produces: `ScoreBadge({ label: string, tone?: "gem" | "neutral" })` — used by `GameCard` (Task 4).

- [ ] **Step 1: Write the failing test**

Create `web/components/ScoreBadge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreBadge } from "./ScoreBadge";

describe("ScoreBadge", () => {
  it("renders the label text", () => {
    render(<ScoreBadge label="숨은 명작" />);
    expect(screen.getByText("숨은 명작")).toBeInTheDocument();
  });

  it("applies the gem tone class when tone is gem", () => {
    render(<ScoreBadge label="숨은 명작" tone="gem" />);
    expect(screen.getByText("숨은 명작")).toHaveClass("text-accent-gem");
  });

  it("applies the neutral tone class by default", () => {
    render(<ScoreBadge label="정보" />);
    expect(screen.getByText("정보")).toHaveClass("text-ink-secondary");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- ScoreBadge.test.tsx`
Expected: FAIL — `./ScoreBadge` module not found.

- [ ] **Step 3: Create `web/components/ScoreBadge.tsx`**

```tsx
type Tone = "gem" | "neutral";

export function ScoreBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  const toneClasses =
    tone === "gem" ? "bg-accent-gem/20 text-accent-gem" : "bg-surface-raised text-ink-secondary";

  return (
    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses}`}>
      {label}
    </span>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- ScoreBadge.test.tsx`
Expected: PASS (3 assertions).

- [ ] **Step 5: Commit**

```bash
git add web/components/ScoreBadge.tsx web/components/ScoreBadge.test.tsx
git commit -m "feat(web): add ScoreBadge component"
```

---

### Task 4: Restyle `GameCard` with Tailwind + `ScoreBadge`

**Files:**
- Modify: `web/components/GameCard.tsx`
- Modify: `web/components/GameCard.test.tsx`

**Interfaces:**
- Consumes: `Gem` from `web/lib/types`; `topPercentileLabel`, `bottomPercentileLabel`, `isHiddenGemZone` from `web/lib/percentile`; `ScoreBadge` from `./ScoreBadge`.
- Produces: `GameCard({ gem: Gem, onSelect?: (gem: Gem) => void })`, still exports `type Gem` (re-exported from `web/lib/types` for backward compatibility with existing imports) — consumed by `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test additions**

Replace the full contents of `web/components/GameCard.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GameCard } from "./GameCard";

const baseGem = {
  app_id: 1,
  name: "Dungeon of Echoes",
  price_cents: 1999,
  genres: ["Indie", "RPG"],
  tags: ["Roguelike"],
  review_score_pct: 93.3,
  review_count: 4500,
  owners_low: 100000,
  owners_high: 200000,
  quality_pctile: 0.9,
  exposure_pctile: 0.2,
  hidden_gem_score: 0.7,
};

describe("GameCard", () => {
  it("renders the game name and percentile-based reasoning", () => {
    render(<GameCard gem={baseGem} />);
    expect(screen.getByText("Dungeon of Echoes")).toBeInTheDocument();
    expect(screen.getByText(/상위 10%/)).toBeInTheDocument();
    expect(screen.getByText(/하위 20%/)).toBeInTheDocument();
  });

  it("shows 무료 for zero price", () => {
    render(<GameCard gem={{ ...baseGem, price_cents: 0 }} />);
    expect(screen.getByText("무료")).toBeInTheDocument();
  });

  it("shows a fallback when price is unknown", () => {
    render(<GameCard gem={{ ...baseGem, price_cents: null }} />);
    expect(screen.getByText("가격 정보 없음")).toBeInTheDocument();
  });

  it("shows 상위 1% (not 상위 0%) when quality_pctile is 1.0", () => {
    render(<GameCard gem={{ ...baseGem, quality_pctile: 1.0 }} />);
    expect(screen.getByText(/상위 1%/)).toBeInTheDocument();
    expect(screen.queryByText(/상위 0%/)).not.toBeInTheDocument();
  });

  it("calls onSelect with the gem when clicked", () => {
    const handleSelect = vi.fn();
    render(<GameCard gem={baseGem} onSelect={handleSelect} />);
    fireEvent.click(screen.getByText("Dungeon of Echoes"));
    expect(handleSelect).toHaveBeenCalledWith(baseGem);
  });

  it("shows a 숨은 명작 badge when the gem is in the hidden-gem zone", () => {
    render(<GameCard gem={{ ...baseGem, quality_pctile: 0.9, exposure_pctile: 0.1 }} />);
    expect(screen.getByText("숨은 명작")).toBeInTheDocument();
  });

  it("does not show the badge outside the hidden-gem zone", () => {
    render(<GameCard gem={{ ...baseGem, quality_pctile: 0.5, exposure_pctile: 0.8 }} />);
    expect(screen.queryByText("숨은 명작")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify the new assertions fail**

Run: `cd web && npm test -- GameCard.test.tsx`
Expected: FAIL — `onSelect` not wired, no badge rendered.

- [ ] **Step 3: Replace the contents of `web/components/GameCard.tsx`**

```tsx
import { bottomPercentileLabel, isHiddenGemZone, topPercentileLabel } from "../lib/percentile";
import type { Gem } from "../lib/types";
import { ScoreBadge } from "./ScoreBadge";

export type { Gem };

function formatPrice(cents: number | null): string {
  if (cents === null) return "가격 정보 없음";
  if (cents === 0) return "무료";
  return `$${(cents / 100).toFixed(2)}`;
}

export function GameCard({ gem, onSelect }: { gem: Gem; onSelect?: (gem: Gem) => void }) {
  const qualityTopPct = topPercentileLabel(gem.quality_pctile);
  const exposureBottomPct = bottomPercentileLabel(gem.exposure_pctile);
  const isGem = isHiddenGemZone(gem.quality_pctile, gem.exposure_pctile);

  return (
    <article
      onClick={() => onSelect?.(gem)}
      className="border-border hover:bg-surface-raised cursor-pointer border-b py-4 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-ink-primary text-base font-semibold">{gem.name}</h3>
        {isGem && <ScoreBadge label="숨은 명작" tone="gem" />}
      </div>
      <p className="text-ink-secondary mt-1 text-sm tabular-nums">{formatPrice(gem.price_cents)}</p>
      <p className="text-ink-secondary mt-2 text-sm">
        장르 내 리뷰 품질 상위 {qualityTopPct}%, 소유자 수는 하위 {exposureBottomPct}%
      </p>
      <p className="text-ink-muted mt-1 text-sm tabular-nums">
        긍정률 {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개 리뷰)
      </p>
    </article>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- GameCard.test.tsx`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add web/components/GameCard.tsx web/components/GameCard.test.tsx
git commit -m "feat(web): restyle GameCard with Tailwind tokens and hidden-gem badge"
```

---

### Task 5: `EmptyState` component

**Files:**
- Create: `web/components/EmptyState.tsx`
- Test: `web/components/EmptyState.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `EmptyState()` — consumed by `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test**

Create `web/components/EmptyState.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("explains why nothing rendered and what to do next", () => {
    render(<EmptyState />);
    expect(screen.getByText("조건에 맞는 게임이 없습니다")).toBeInTheDocument();
    expect(screen.getByText(/다시 검색해보세요/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- EmptyState.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/components/EmptyState.tsx`**

```tsx
export function EmptyState() {
  return (
    <div className="border-border rounded-lg border border-dashed py-16 text-center">
      <p className="text-ink-primary text-base font-medium">조건에 맞는 게임이 없습니다</p>
      <p className="text-ink-secondary mt-1 text-sm">
        장르나 태그를 줄이거나 예산을 늘려서 다시 검색해보세요.
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- EmptyState.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/components/EmptyState.tsx web/components/EmptyState.test.tsx
git commit -m "feat(web): add EmptyState component"
```

---

### Task 6: Filter query pure functions

**Files:**
- Create: `web/lib/filterQuery.ts`
- Test: `web/lib/filterQuery.test.ts`

**Interfaces:**
- Consumes: `Filters` from `web/lib/types`.
- Produces: `DEFAULT_FILTERS: Filters`; `parseFiltersFromSearchParams(params: URLSearchParams): Filters`; `buildSearchParams(filters: Filters): URLSearchParams`; `buildApiQuery(filters: Filters, limit: number): URLSearchParams` — consumed by `FilterPanel` (Task 7, via the page) and `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test**

Create `web/lib/filterQuery.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { DEFAULT_FILTERS, buildApiQuery, buildSearchParams, parseFiltersFromSearchParams } from "./filterQuery";

describe("parseFiltersFromSearchParams", () => {
  it("falls back to defaults when the URL has no filters", () => {
    expect(parseFiltersFromSearchParams(new URLSearchParams())).toEqual(DEFAULT_FILTERS);
  });

  it("reads genre, tag, and maxPrice from the URL", () => {
    const params = new URLSearchParams("genre=simulation&tag=Roguelike&maxPrice=20");
    expect(parseFiltersFromSearchParams(params)).toEqual({
      genre: "simulation",
      tag: "Roguelike",
      maxPrice: "20",
    });
  });
});

describe("buildSearchParams", () => {
  it("always includes genre and omits empty tag/maxPrice", () => {
    const params = buildSearchParams({ genre: "indie", tag: "", maxPrice: "" });
    expect(params.toString()).toBe("genre=indie");
  });

  it("round-trips through parseFiltersFromSearchParams", () => {
    const filters = { genre: "simulation", tag: "Roguelike", maxPrice: "20" };
    expect(parseFiltersFromSearchParams(buildSearchParams(filters))).toEqual(filters);
  });
});

describe("buildApiQuery", () => {
  it("converts maxPrice in USD to max_price_cents", () => {
    const params = buildApiQuery({ genre: "indie", tag: "", maxPrice: "15" }, 200);
    expect(params.get("max_price_cents")).toBe("1500");
  });

  it("omits max_price_cents when maxPrice is empty", () => {
    const params = buildApiQuery({ genre: "indie", tag: "", maxPrice: "" }, 200);
    expect(params.has("max_price_cents")).toBe(false);
  });

  it("includes the limit", () => {
    const params = buildApiQuery(DEFAULT_FILTERS, 200);
    expect(params.get("limit")).toBe("200");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- filterQuery.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/lib/filterQuery.ts`**

```ts
import type { Filters } from "./types";

export const DEFAULT_FILTERS: Filters = { genre: "indie", tag: "", maxPrice: "" };

export function parseFiltersFromSearchParams(params: URLSearchParams): Filters {
  return {
    genre: params.get("genre") ?? DEFAULT_FILTERS.genre,
    tag: params.get("tag") ?? DEFAULT_FILTERS.tag,
    maxPrice: params.get("maxPrice") ?? DEFAULT_FILTERS.maxPrice,
  };
}

export function buildSearchParams(filters: Filters): URLSearchParams {
  const params = new URLSearchParams();
  params.set("genre", filters.genre);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.maxPrice) params.set("maxPrice", filters.maxPrice);
  return params;
}

export function buildApiQuery(filters: Filters, limit: number): URLSearchParams {
  const params = new URLSearchParams({ genre: filters.genre, limit: String(limit) });
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.maxPrice) {
    params.set("max_price_cents", String(Number(filters.maxPrice) * 100));
  }
  return params;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- filterQuery.test.ts`
Expected: PASS (7 assertions).

- [ ] **Step 5: Commit**

```bash
git add web/lib/filterQuery.ts web/lib/filterQuery.test.ts
git commit -m "feat(web): add filter query-string pure helpers"
```

---

### Task 7: `FilterPanel` component

**Files:**
- Create: `web/components/FilterPanel.tsx`
- Test: `web/components/FilterPanel.test.tsx`

**Interfaces:**
- Consumes: `Filters` from `web/lib/types`.
- Produces: `FilterPanel({ filters: Filters, loading: boolean, onChange: (filters: Filters) => void, onSubmit: () => void })` — consumed by `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test**

Create `web/components/FilterPanel.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FilterPanel } from "./FilterPanel";

const baseFilters = { genre: "indie", tag: "", maxPrice: "" };

describe("FilterPanel", () => {
  it("calls onChange with the updated genre", () => {
    const onChange = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={onChange} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("장르"), { target: { value: "simulation" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, genre: "simulation" });
  });

  it("calls onChange with the updated tag", () => {
    const onChange = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={onChange} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("태그"), { target: { value: "Roguelike" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, tag: "Roguelike" });
  });

  it("calls onSubmit when the form is submitted", () => {
    const onSubmit = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={vi.fn()} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "검색" }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("disables the submit button while loading", () => {
    render(<FilterPanel filters={baseFilters} loading={true} onChange={vi.fn()} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "검색 중..." })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- FilterPanel.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/components/FilterPanel.tsx`**

```tsx
import type { Filters } from "../lib/types";

const GENRE_OPTIONS = [
  { value: "indie", label: "인디" },
  { value: "simulation", label: "시뮬레이션" },
];

export function FilterPanel({
  filters,
  loading,
  onChange,
  onSubmit,
}: {
  filters: Filters;
  loading: boolean;
  onChange: (filters: Filters) => void;
  onSubmit: () => void;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="bg-surface border-border flex flex-col gap-4 rounded-lg border p-5"
    >
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        장르
        <select
          value={filters.genre}
          onChange={(e) => onChange({ ...filters, genre: e.target.value })}
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        >
          {GENRE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        태그
        <input
          type="text"
          value={filters.tag}
          onChange={(e) => onChange({ ...filters, tag: e.target.value })}
          placeholder="Roguelike"
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        />
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        최대 예산 (USD)
        <input
          type="number"
          value={filters.maxPrice}
          onChange={(e) => onChange({ ...filters, maxPrice: e.target.value })}
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        />
      </label>
      <button
        type="submit"
        disabled={loading}
        className="bg-accent-gem rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {loading ? "검색 중..." : "검색"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- FilterPanel.test.tsx`
Expected: PASS (4 assertions).

- [ ] **Step 5: Commit**

```bash
git add web/components/FilterPanel.tsx web/components/FilterPanel.test.tsx
git commit -m "feat(web): add FilterPanel component"
```

---

### Task 8: `GemScatterChart` component

**Files:**
- Create: `web/components/GemScatterChart.tsx`
- Test: `web/components/GemScatterChart.test.tsx`

**Interfaces:**
- Consumes: `Gem` from `web/lib/types`; `isHiddenGemZone` from `web/lib/percentile`.
- Produces: `GemScatterChart({ gems: Gem[], onSelect?: (gem: Gem) => void })` — consumed by `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test**

Create `web/components/GemScatterChart.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GemScatterChart } from "./GemScatterChart";

const gemInZone = {
  app_id: 1,
  name: "Dungeon of Echoes",
  price_cents: 1999,
  genres: ["Indie"],
  tags: ["Roguelike"],
  review_score_pct: 93.3,
  review_count: 4500,
  owners_low: 100000,
  owners_high: 200000,
  quality_pctile: 0.9,
  exposure_pctile: 0.1,
  hidden_gem_score: 0.8,
};

const gemOutsideZone = {
  ...gemInZone,
  app_id: 2,
  name: "Popular Hit",
  quality_pctile: 0.5,
  exposure_pctile: 0.9,
};

describe("GemScatterChart", () => {
  it("renders one point per gem", () => {
    render(<GemScatterChart gems={[gemInZone, gemOutsideZone]} />);
    expect(screen.getByTestId("point-1")).toBeInTheDocument();
    expect(screen.getByTestId("point-2")).toBeInTheDocument();
  });

  it("colors a hidden-gem-zone point with the accent color", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    expect(screen.getByTestId("point-1")).toHaveAttribute("fill", "#7c6af0");
  });

  it("colors a point outside the zone with the muted color", () => {
    render(<GemScatterChart gems={[gemOutsideZone]} />);
    expect(screen.getByTestId("point-2")).toHaveAttribute("fill", "#6a6f7e");
  });

  it("shows the game name on hover", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    fireEvent.mouseEnter(screen.getByTestId("point-1"));
    expect(screen.getByText("Dungeon of Echoes")).toBeInTheDocument();
  });

  it("calls onSelect when a point is clicked", () => {
    const onSelect = vi.fn();
    render(<GemScatterChart gems={[gemInZone]} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("point-1"));
    expect(onSelect).toHaveBeenCalledWith(gemInZone);
  });

  it("toggles to a table view with the same data", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    fireEvent.click(screen.getByRole("button", { name: "표로 보기" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Dungeon of Echoes" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- GemScatterChart.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/components/GemScatterChart.tsx`**

```tsx
"use client";

import { useState } from "react";

import { isHiddenGemZone } from "../lib/percentile";
import type { Gem } from "../lib/types";

const WIDTH = 480;
const HEIGHT = 360;
const PADDING = 32;
const PLOT_WIDTH = WIDTH - PADDING * 2;
const PLOT_HEIGHT = HEIGHT - PADDING * 2;
const GEM_ZONE_MAX_EXPOSURE = 0.3;
const GEM_ZONE_MIN_QUALITY = 0.7;
const ACCENT_GEM = "#7c6af0";
const INK_MUTED = "#6a6f7e";

function toX(exposurePctile: number): number {
  return PADDING + exposurePctile * PLOT_WIDTH;
}

function toY(qualityPctile: number): number {
  return PADDING + (1 - qualityPctile) * PLOT_HEIGHT;
}

export function GemScatterChart({
  gems,
  onSelect,
}: {
  gems: Gem[];
  onSelect?: (gem: Gem) => void;
}) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const hovered = gems.find((g) => g.app_id === hoveredId) ?? null;

  return (
    <div className="bg-surface border-border rounded-lg border p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-ink-primary text-base font-semibold">품질 대비 노출 사분면</h2>
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="text-ink-secondary text-xs underline"
        >
          {showTable ? "차트로 보기" : "표로 보기"}
        </button>
      </div>
      {showTable ? (
        <table className="text-ink-secondary w-full text-left text-sm">
          <thead>
            <tr>
              <th className="pb-2">게임</th>
              <th className="pb-2">품질 백분위</th>
              <th className="pb-2">노출 백분위</th>
            </tr>
          </thead>
          <tbody>
            {gems.map((gem) => (
              <tr key={gem.app_id} className="border-border border-t">
                <td className="py-1.5">{gem.name}</td>
                <td className="py-1.5 tabular-nums">{Math.round(gem.quality_pctile * 100)}%</td>
                <td className="py-1.5 tabular-nums">{Math.round(gem.exposure_pctile * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label="품질 백분위 대 노출 백분위 산점도"
          className="w-full"
        >
          <rect
            x={PADDING}
            y={PADDING}
            width={GEM_ZONE_MAX_EXPOSURE * PLOT_WIDTH}
            height={(1 - GEM_ZONE_MIN_QUALITY) * PLOT_HEIGHT}
            fill={ACCENT_GEM}
            fillOpacity={0.12}
          />
          <text x={PADDING + 4} y={PADDING + 14} fill={ACCENT_GEM} fontSize={10}>
            숨은 명작 구간
          </text>
          <line
            x1={PADDING}
            y1={HEIGHT - PADDING}
            x2={WIDTH - PADDING}
            y2={HEIGHT - PADDING}
            stroke="#2e3340"
          />
          <line x1={PADDING} y1={PADDING} x2={PADDING} y2={HEIGHT - PADDING} stroke="#2e3340" />
          {gems.map((gem) => {
            const isGem = isHiddenGemZone(gem.quality_pctile, gem.exposure_pctile);
            return (
              <circle
                key={gem.app_id}
                data-testid={`point-${gem.app_id}`}
                cx={toX(gem.exposure_pctile)}
                cy={toY(gem.quality_pctile)}
                r={5}
                fill={isGem ? ACCENT_GEM : INK_MUTED}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredId(gem.app_id)}
                onMouseLeave={() => setHoveredId((id) => (id === gem.app_id ? null : id))}
                onClick={() => onSelect?.(gem)}
              />
            );
          })}
          {hovered && (
            <text
              x={toX(hovered.exposure_pctile) + 8}
              y={toY(hovered.quality_pctile) - 8}
              fill="#edeef2"
              fontSize={11}
            >
              {hovered.name}
            </text>
          )}
        </svg>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- GemScatterChart.test.tsx`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add web/components/GemScatterChart.tsx web/components/GemScatterChart.test.tsx
git commit -m "feat(web): add GemScatterChart with gem-zone highlight and table fallback"
```

---

### Task 9: `GameDetailModal` component

**Files:**
- Create: `web/components/GameDetailModal.tsx`
- Test: `web/components/GameDetailModal.test.tsx`

**Interfaces:**
- Consumes: `Gem` from `web/lib/types`; `topPercentileLabel`, `bottomPercentileLabel` from `web/lib/percentile`.
- Produces: `GameDetailModal({ gem: Gem, onClose: () => void })` — consumed by `app/page.tsx` (Task 10).

- [ ] **Step 1: Write the failing test**

Create `web/components/GameDetailModal.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GameDetailModal } from "./GameDetailModal";

const gem = {
  app_id: 1,
  name: "Dungeon of Echoes",
  price_cents: 1999,
  genres: ["Indie"],
  tags: ["Roguelike", "Turn-Based"],
  review_score_pct: 93.3,
  review_count: 4500,
  owners_low: 100000,
  owners_high: 200000,
  quality_pctile: 0.9,
  exposure_pctile: 0.2,
  hidden_gem_score: 0.7,
};

describe("GameDetailModal", () => {
  it("shows the game's name, percentile breakdown, and tags", () => {
    render(<GameDetailModal gem={gem} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Dungeon of Echoes" })).toBeInTheDocument();
    expect(screen.getByText("상위 10%")).toBeInTheDocument();
    expect(screen.getByText("하위 20%")).toBeInTheDocument();
    expect(screen.getByText("Roguelike")).toBeInTheDocument();
  });

  it("calls onClose when the backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("presentation"));
    expect(onClose).toHaveBeenCalled();
  });

  it("does not call onClose when the dialog content is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when the close button is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- GameDetailModal.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/components/GameDetailModal.tsx`**

```tsx
"use client";

import { useEffect } from "react";

import { bottomPercentileLabel, topPercentileLabel } from "../lib/percentile";
import type { Gem } from "../lib/types";

export function GameDetailModal({ gem, onClose }: { gem: Gem; onClose: () => void }) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const qualityTopPct = topPercentileLabel(gem.quality_pctile);
  const exposureBottomPct = bottomPercentileLabel(gem.exposure_pctile);

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={gem.name}
        onClick={(e) => e.stopPropagation()}
        className="bg-surface-raised border-border max-h-[80vh] w-full max-w-md overflow-y-auto rounded-lg border p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-ink-primary text-lg font-semibold">{gem.name}</h2>
          <button type="button" onClick={onClose} aria-label="닫기" className="text-ink-secondary text-sm">
            닫기
          </button>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-ink-secondary">품질 백분위</dt>
          <dd className="text-ink-primary tabular-nums">상위 {qualityTopPct}%</dd>
          <dt className="text-ink-secondary">노출 백분위</dt>
          <dd className="text-ink-primary tabular-nums">하위 {exposureBottomPct}%</dd>
          <dt className="text-ink-secondary">긍정률</dt>
          <dd className="text-ink-primary tabular-nums">
            {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개)
          </dd>
        </dl>
        <p className="text-ink-secondary mt-4 text-sm">
          장르 내 리뷰 품질은 상위 {qualityTopPct}%인데, 소유자 수는 하위 {exposureBottomPct}%에 그쳐
          저평가로 판정됐습니다.
        </p>
        {gem.tags.length > 0 && (
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {gem.tags.map((tag) => (
              <li key={tag} className="bg-surface text-ink-secondary rounded-full px-2.5 py-1 text-xs">
                {tag}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- GameDetailModal.test.tsx`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add web/components/GameDetailModal.tsx web/components/GameDetailModal.test.tsx
git commit -m "feat(web): add GameDetailModal with score breakdown"
```

---

### Task 10: Rewire `app/page.tsx`

**Files:**
- Modify: `web/app/page.tsx`
- Create: `web/app/page.test.tsx`

**Interfaces:**
- Consumes: `Gem` from `web/lib/types`; `buildApiQuery`, `buildSearchParams`, `parseFiltersFromSearchParams` from `web/lib/filterQuery`; `FilterPanel` (Task 7); `GemScatterChart` (Task 8); `GameCard` (Task 4); `GameDetailModal` (Task 9); `EmptyState` (Task 5).
- Produces: the composed page — nothing downstream consumes this task's output.

- [ ] **Step 1: Write the failing test**

Create `web/app/page.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

import HomePage from "./page";

const sampleGem = {
  app_id: 1,
  name: "Dungeon of Echoes",
  price_cents: 1999,
  genres: ["Indie"],
  tags: ["Roguelike"],
  review_score_pct: 93.3,
  review_count: 4500,
  owners_low: 100000,
  owners_high: 200000,
  quality_pctile: 0.9,
  exposure_pctile: 0.1,
  hidden_gem_score: 0.8,
};

beforeEach(() => {
  replace.mockClear();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      json: () => Promise.resolve([sampleGem]),
    })
  );
});

describe("HomePage", () => {
  it("fetches and renders gems on load", async () => {
    render(<HomePage />);
    await waitFor(() => screen.getByText("Dungeon of Echoes"));
    expect(global.fetch).toHaveBeenCalled();
  });

  it("shows the empty state when no gems match", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      json: () => Promise.resolve([]),
    });
    render(<HomePage />);
    await waitFor(() => screen.getByText("조건에 맞는 게임이 없습니다"));
  });

  it("opens the detail modal when a card is clicked", async () => {
    render(<HomePage />);
    await waitFor(() => screen.getByText("Dungeon of Echoes"));
    fireEvent.click(screen.getByText("Dungeon of Echoes"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- page.test.tsx`
Expected: FAIL — current `page.tsx` doesn't use `next/navigation`, doesn't render a dialog, doesn't show `EmptyState`.

- [ ] **Step 3: Replace the contents of `web/app/page.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "../components/EmptyState";
import { FilterPanel } from "../components/FilterPanel";
import { GameCard } from "../components/GameCard";
import { GameDetailModal } from "../components/GameDetailModal";
import { GemScatterChart } from "../components/GemScatterChart";
import { buildApiQuery, buildSearchParams, parseFiltersFromSearchParams } from "../lib/filterQuery";
import type { Filters, Gem } from "../lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const CHART_LIMIT = 200;
const CARD_LIMIT = 30;

export default function HomePage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<Filters>(() => parseFiltersFromSearchParams(searchParams));
  const [gems, setGems] = useState<Gem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Gem | null>(null);

  const runSearch = useCallback(
    async (nextFilters: Filters) => {
      setLoading(true);
      const query = buildApiQuery(nextFilters, CHART_LIMIT);
      const response = await fetch(`${API_BASE}/games/gems?${query.toString()}`);
      const data: Gem[] = await response.json();
      setGems(data);
      setLoading(false);
      router.replace(`${pathname}?${buildSearchParams(nextFilters).toString()}`);
    },
    [pathname, router]
  );

  useEffect(() => {
    runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="mx-auto max-w-[1120px] px-6 py-10">
      <header className="flex items-center justify-between">
        <span className="text-ink-primary text-sm font-semibold">Steam Hidden Gems</span>
        <a href="/about" className="text-ink-secondary text-sm">
          방법론
        </a>
      </header>
      <h1 className="text-ink-primary mt-8 text-[28px] font-bold sm:text-[40px]">
        리뷰는 좋은데 아무도 모르는 게임을 찾습니다
      </h1>
      <p className="text-ink-secondary mt-2 text-sm">
        장르·태그·예산을 고르면 품질 대비 저평가된 게임을 백분위 근거와 함께 보여줍니다.
      </p>
      <div className="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]">
        <FilterPanel
          filters={filters}
          loading={loading}
          onChange={setFilters}
          onSubmit={() => runSearch(filters)}
        />
        <GemScatterChart gems={gems} onSelect={setSelected} />
      </div>
      <section className="mt-8">
        {gems.length === 0 && !loading ? (
          <EmptyState />
        ) : (
          <div className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
            {gems.slice(0, CARD_LIMIT).map((gem) => (
              <GameCard key={gem.app_id} gem={gem} onSelect={setSelected} />
            ))}
          </div>
        )}
      </section>
      {selected && <GameDetailModal gem={selected} onClose={() => setSelected(null)} />}
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- page.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full web test suite**

Run: `cd web && npm test`
Expected: PASS — all suites (Tasks 1–10 combined) green.

- [ ] **Step 6: Commit**

```bash
git add web/app/page.tsx web/app/page.test.tsx
git commit -m "feat(web): compose FilterPanel, GemScatterChart, GameCard grid, and detail modal on the home page"
```

---

### Task 11: `/about` methodology page

**Files:**
- Create: `web/app/about/page.tsx`
- Test: `web/app/about/page.test.tsx`

**Interfaces:**
- Consumes: nothing (static content).
- Produces: nothing consumed by later tasks — linked to from `app/page.tsx` header (already wired in Task 10 via `<a href="/about">`).

- [ ] **Step 1: Write the failing test**

Create `web/app/about/page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AboutPage from "./page";

describe("AboutPage", () => {
  it("leads with the conclusion: what counts as underrated", () => {
    render(<AboutPage />);
    expect(
      screen.getByText("리뷰 품질은 높은데 아무도 모르는 게임을 어떻게 찾나요")
    ).toBeInTheDocument();
  });

  it("documents a known limitation of the owners estimate", () => {
    render(<AboutPage />);
    expect(screen.getByText(/SteamSpy의 추정 구간값/)).toBeInTheDocument();
  });

  it("links back to the home page", () => {
    render(<AboutPage />);
    expect(screen.getByRole("link", { name: /돌아가기/ })).toHaveAttribute("href", "/");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm test -- about/page.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/app/about/page.tsx`**

```tsx
export default function AboutPage() {
  return (
    <main className="mx-auto max-w-[720px] px-6 py-10">
      <a href="/" className="text-ink-secondary text-sm">
        ← 돌아가기
      </a>
      <h1 className="text-ink-primary mt-6 text-2xl font-bold">
        리뷰 품질은 높은데 아무도 모르는 게임을 어떻게 찾나요
      </h1>
      <p className="text-ink-primary mt-4 text-base leading-7">
        리뷰 긍정률이 코호트(같은 장르·같은 출시연도) 평균보다 높으면서, 소유자 추정치는 하위권인
        게임을 저평가로 판정합니다. 리뷰 수가 적어 극단값이 나오는 걸 막기 위해 베이지안 보정을
        거친 뒤, 같은 코호트 안에서 백분위로 비교합니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">데이터 소스</h2>
      <p className="text-ink-secondary mt-2 text-sm leading-6">
        게임 정보와 리뷰 긍정률은 Steam 공식 Web API에서, 소유자 수 추정 구간은 SteamSpy에서
        가져옵니다. 두 소스 모두 매일 배치로 갱신됩니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">한계</h2>
      <ul className="text-ink-secondary mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6">
        <li>owners는 SteamSpy의 추정 구간값이라 실제 판매량과 오차가 있을 수 있습니다.</li>
        <li>리뷰 수 자체가 어뷰징이나 봇의 영향을 받을 수 있으며, 별도 이상치 제거는 하지 않습니다.</li>
        <li>같은 장르·연도 조합의 게임 수가 적으면 장르만으로 비교 범위를 넓힙니다.</li>
      </ul>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm test -- about/page.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/app/about/page.tsx web/app/about/page.test.tsx
git commit -m "feat(web): add /about methodology page"
```

---

### Task 12: Update README

**Files:**
- Modify: `README.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update the "웹앱 (`web/`)" section**

In `README.md`, replace the existing `## 웹앱 (\`web/\`)` section body with:

```markdown
## 웹앱 (`web/`)

```bash
cd web
npm install
npm run dev
```

Next.js(App Router) + Tailwind CSS로 만든 검색 UI로, `NEXT_PUBLIC_API_BASE_URL`
(기본값 `http://localhost:8000`)로 FastAPI 서버에 요청해 결과를 렌더링한다.
필터 상태는 URL 쿼리스트링에 유지된다.

- `/` — 필터(장르/태그/예산), 품질·노출 백분위 사분면 산점도, 랭킹 카드 그리드.
  카드나 산점도 점을 클릭하면 점수 근거를 보여주는 상세 모달이 열린다.
- `/about` — 스코어링 로직·데이터 소스·한계를 설명하는 방법론 페이지.

디자인 토큰(`web/app/globals.css`)과 컴포넌트 인벤토리는
[웹앱 디자인 시스템 설계 문서](docs/superpowers/specs/2026-09-06-webapp-design-system-design.md)에
정리돼 있다.

테스트:

```bash
cd web
npm test
```
```

- [ ] **Step 2: Verify the section renders correctly**

Run: `cat README.md` and visually confirm the new section replaced the old one without duplicating headers.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the redesigned webapp and /about page"
```

---

### Task 13: Manual visual QA with real data

This task has no automated test — it is the final human-in-the-loop check that the design system reads correctly against real Steam/SteamSpy data, per the design doc's risk note that the app was built against fixtures.

**Files:** none (verification only, may produce follow-up bug-fix commits if issues are found).

- [ ] **Step 1: Seed the local database with real data**

Ensure `.env` has a real `STEAM_API_KEY` (get one at `steamcommunity.com/dev/apikey`, Domain Name = `localhost`), then run:

```bash
docker compose up -d
alembic upgrade head
python scripts/run_pipeline.py
```

Expected: `pipeline_runs` gets a row with `status = 'ok'` and `games_collected > 0`.

- [ ] **Step 2: Start the API and the web app**

```bash
uvicorn tracker.api.app:app --reload &
cd web && npm run dev
```

- [ ] **Step 3: Walk through the golden path in a browser**

Open `http://localhost:3000` and check:
- The headline and scatter chart render with real games (not empty).
- Changing genre/tag/max-budget and clicking 검색 updates both the chart and the card grid, and the URL query string updates.
- The gem-zone highlight in the chart visually corresponds to the "숨은 명작" badges in the card grid.
- Clicking a card and a chart point both open the same detail modal with correct percentile numbers.
- Escape and backdrop click both close the modal.
- `표로 보기` toggles to an accessible table with the same games.
- `/about` renders and its "← 돌아가기" link returns to `/`.
- Resize the window to a mobile width (~375px) and confirm the layout stacks to one column without horizontal scroll.

- [ ] **Step 4: Fix anything broken**

If a step in Step 3 fails, fix it in the relevant component from Tasks 1–11, re-run that component's test file, and commit the fix with a `fix(web): ...` message.

---

## Self-Review Notes

- **Spec coverage:** color tokens (Task 1), Pretendard (Task 1), ScoreBadge/GameCard/EmptyState/FilterPanel (Tasks 3–7), quadrant scatter chart with gem-zone highlight + hover + table fallback (Task 8), detail modal (Task 9), URL-query-string state (Tasks 6, 10), `/about` methodology page (Task 11), README (Task 12), real-data validation (Task 13) — all spec sections are covered.
- **No placeholders:** every step has runnable code, not descriptions.
- **Type consistency:** `Gem` and `Filters` are defined once in `web/lib/types.ts` (Task 2) and imported by every later task; `isHiddenGemZone`, `topPercentileLabel`, `bottomPercentileLabel` are defined once in `web/lib/percentile.ts` (Task 2) and reused by `GameCard` (Task 4) and `GemScatterChart`/`GameDetailModal` (Tasks 8–9) rather than reimplemented.
