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
