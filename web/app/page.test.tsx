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
