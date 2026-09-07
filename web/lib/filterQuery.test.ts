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
