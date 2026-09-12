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

/** One selectable filter value from /genres or /tags, with how many scored
 * games carry it. Served by the API rather than hardcoded, because the
 * hardcoded genre list went stale without anyone noticing. */
export type Facet = {
  value: string;
  count: number;
};

export type Filters = {
  genre: string;
  tag: string;
  maxPrice: string;
};
