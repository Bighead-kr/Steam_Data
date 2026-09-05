import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
});
