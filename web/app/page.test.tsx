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

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: () => Promise.resolve(body) };
}

/** Routes each endpoint the page calls; `gems` overrides just that one. */
function stubApi(gems: unknown = [sampleGem]) {
  const fetchMock = vi.fn((url: string) => {
    if (url.includes("/genres")) return Promise.resolve(jsonResponse([{ value: "indie", count: 3 }]));
    if (url.includes("/tags")) return Promise.resolve(jsonResponse([{ value: "Roguelike", count: 2 }]));
    return Promise.resolve(jsonResponse(gems));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  replace.mockClear();
  stubApi();
});

describe("HomePage", () => {
  it("renders the heading without waiting for any data", () => {
    /** The heading and the explanation are server-rendered, outside the
     * Suspense boundary - the page used to bail out to client rendering
     * entirely and ship an empty <body>. */
    render(<HomePage />);
    expect(screen.getByText("리뷰는 좋은데 아무도 모르는 게임을 찾습니다")).toBeInTheDocument();
  });

  it("fetches and renders gems on load", async () => {
    render(<HomePage />);
    await waitFor(() => screen.getByText("Dungeon of Echoes"));
    expect(global.fetch).toHaveBeenCalled();
  });

  it("shows the empty state when no gems match", async () => {
    stubApi([]);
    render(<HomePage />);
    await waitFor(() => screen.getByText("조건에 맞는 게임이 없습니다"));
  });

  it("opens the detail modal when a card is clicked", async () => {
    render(<HomePage />);
    await waitFor(() => screen.getByText("Dungeon of Echoes"));
    fireEvent.click(screen.getByText("Dungeon of Echoes"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows an error state, not a stuck spinner, when the API fails", async () => {
    /** The free Render plan sleeps; the first request after that can take
     * most of a minute or fail outright. The old page had no catch and no
     * response.ok check, so a failure left the button reading "검색 중..."
     * forever with nothing on screen. */
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(null, false, 503)));
    render(<HomePage />);
    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByText(/503/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "검색" })).not.toBeDisabled();
  });

  it("shows an error state when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<HomePage />);
    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByText(/서버에 연결하지 못했습니다/)).toBeInTheDocument();
  });

  it("does not crash when the API answers with something that isn't a list", async () => {
    stubApi({ detail: "Internal Server Error" });
    render(<HomePage />);
    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByText(/형식이 올바르지 않습니다/)).toBeInTheDocument();
  });
});
