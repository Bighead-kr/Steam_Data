import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchGems, fetchGenres, fetchTags } from "./api";

const filters = { genre: "indie", tag: "", maxPrice: "" };

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: () => Promise.resolve(body) };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchGems", () => {
  it("returns the parsed list", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([{ app_id: 1 }])));
    await expect(fetchGems(filters, 200)).resolves.toEqual([{ app_id: 1 }]);
  });

  it("sends the filters and limit as query parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    await fetchGems({ genre: "simulation", tag: "Roguelike", maxPrice: "20" }, 200);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("genre=simulation");
    expect(url).toContain("tag=Roguelike");
    expect(url).toContain("max_price_cents=2000");
    expect(url).toContain("limit=200");
  });

  it("raises a readable error on an HTTP failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(null, false, 503)));
    await expect(fetchGems(filters, 200)).rejects.toThrow(ApiError);
    await expect(fetchGems(filters, 200)).rejects.toThrow(/503/);
  });

  it("raises a readable error when the server can't be reached", async () => {
    /** The free Render plan sleeps, so this is the ordinary first-visit
     * failure, not an exotic one. */
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchGems(filters, 200)).rejects.toThrow(/연결하지 못했습니다/);
  });

  it("raises rather than returning a non-list body", async () => {
    /** A 200 carrying an error object used to reach the render path and
     * crash on .slice. */
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "boom" })));
    await expect(fetchGems(filters, 200)).rejects.toThrow(/형식이 올바르지 않습니다/);
  });

  it("propagates an abort instead of reporting it as a server error", async () => {
    const abort = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(fetchGems(filters, 200)).rejects.toBe(abort);
  });
});

describe("facet endpoints", () => {
  it("fetchGenres reads /genres", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([{ value: "indie", count: 3 }]));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchGenres()).resolves.toEqual([{ value: "indie", count: 3 }]);
    expect(fetchMock.mock.calls[0][0]).toContain("/genres");
  });

  it("fetchTags scopes to a genre", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    await fetchTags("simulation");
    expect(fetchMock.mock.calls[0][0]).toContain("/tags?genre=simulation");
  });
});
