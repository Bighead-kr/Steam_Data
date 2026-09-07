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
