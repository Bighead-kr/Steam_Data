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
