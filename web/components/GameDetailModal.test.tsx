import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GameDetailModal } from "./GameDetailModal";

const gem = {
  app_id: 1,
  name: "Dungeon of Echoes",
  price_cents: 1999,
  genres: ["Indie"],
  tags: ["Roguelike", "Turn-Based"],
  review_score_pct: 93.3,
  review_count: 4500,
  owners_low: 100000,
  owners_high: 200000,
  quality_pctile: 0.9,
  exposure_pctile: 0.2,
  hidden_gem_score: 0.7,
};

describe("GameDetailModal", () => {
  it("shows the game's name, percentile breakdown, and tags", () => {
    render(<GameDetailModal gem={gem} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Dungeon of Echoes" })).toBeInTheDocument();
    expect(screen.getByText("상위 10%")).toBeInTheDocument();
    expect(screen.getByText("하위 20%")).toBeInTheDocument();
    expect(screen.getByText("Roguelike")).toBeInTheDocument();
  });

  it("calls onClose when the backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("presentation"));
    expect(onClose).toHaveBeenCalled();
  });

  it("does not call onClose when the dialog content is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when the close button is clicked", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<GameDetailModal gem={gem} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
