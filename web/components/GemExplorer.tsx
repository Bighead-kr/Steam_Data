"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError, fetchGems, fetchGenres, fetchTags } from "../lib/api";
import { buildSearchParams, parseFiltersFromSearchParams } from "../lib/filterQuery";
import type { Facet, Filters, Gem } from "../lib/types";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { FilterPanel } from "./FilterPanel";
import { GameCard } from "./GameCard";
import { GameDetailModal } from "./GameDetailModal";
import { GemScatterChart } from "./GemScatterChart";

const CHART_LIMIT = 200;
const CARD_LIMIT = 30;

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "알 수 없는 오류가 발생했습니다.";
}

export function GemExplorer() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<Filters>(() => parseFiltersFromSearchParams(searchParams));
  const [gems, setGems] = useState<Gem[]>([]);
  const [genres, setGenres] = useState<Facet[]>([]);
  const [tags, setTags] = useState<Facet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Gem | null>(null);
  // Two searches in flight (a fast one started second, a slow one started
  // first) used to race, and the slower response won. Only the newest
  // request is allowed to write state.
  const latestRequest = useRef(0);

  const runSearch = useCallback(
    async (nextFilters: Filters) => {
      const requestId = ++latestRequest.current;
      setLoading(true);
      setError(null);
      try {
        const data = await fetchGems(nextFilters, CHART_LIMIT);
        if (requestId !== latestRequest.current) return;
        setGems(data);
      } catch (caught) {
        if (requestId !== latestRequest.current) return;
        setGems([]);
        setError(errorMessage(caught));
      } finally {
        if (requestId === latestRequest.current) setLoading(false);
      }
      router.replace(`${pathname}?${buildSearchParams(nextFilters).toString()}`);
    },
    [pathname, router]
  );

  useEffect(() => {
    runSearch(filters);
    // Initial load only; later searches are driven by the form.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchGenres(controller.signal)
      .then(setGenres)
      // The filter panel falls back to the genre already in the URL, so a
      // failed facet lookup degrades the form instead of breaking the page.
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchTags(filters.genre, controller.signal)
      .then(setTags)
      .catch(() => undefined);
    return () => controller.abort();
  }, [filters.genre]);

  const handleFilterChange = useCallback((next: Filters) => {
    // Tag vocabularies barely overlap between genres, so a tag carried over
    // from the previous genre is almost always a guaranteed zero-result
    // search.
    setFilters((current) => (current.genre === next.genre ? next : { ...next, tag: "" }));
  }, []);

  return (
    <>
      <div className="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]">
        <FilterPanel
          filters={filters}
          genres={genres}
          tags={tags}
          loading={loading}
          onChange={handleFilterChange}
          onSubmit={() => runSearch(filters)}
        />
        <GemScatterChart gems={gems} onSelect={setSelected} />
      </div>
      <section className="mt-8">
        {error ? (
          <ErrorState message={error} onRetry={() => runSearch(filters)} />
        ) : gems.length === 0 && !loading ? (
          <EmptyState />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {gems.slice(0, CARD_LIMIT).map((gem) => (
              <GameCard key={gem.app_id} gem={gem} onSelect={setSelected} />
            ))}
          </div>
        )}
      </section>
      {selected && <GameDetailModal gem={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
