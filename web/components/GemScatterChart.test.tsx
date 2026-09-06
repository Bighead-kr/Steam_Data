import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GemScatterChart } from "./GemScatterChart";

const gemInZone = {
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

const gemOutsideZone = {
  ...gemInZone,
  app_id: 2,
  name: "Popular Hit",
  quality_pctile: 0.5,
  exposure_pctile: 0.9,
};

describe("GemScatterChart", () => {
  it("renders one point per gem", () => {
    render(<GemScatterChart gems={[gemInZone, gemOutsideZone]} />);
    expect(screen.getByTestId("point-1")).toBeInTheDocument();
    expect(screen.getByTestId("point-2")).toBeInTheDocument();
  });

  it("colors a hidden-gem-zone point with the accent color", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    expect(screen.getByTestId("point-1")).toHaveAttribute("fill", "#7c6af0");
  });

  it("colors a point outside the zone with the muted color", () => {
    render(<GemScatterChart gems={[gemOutsideZone]} />);
    expect(screen.getByTestId("point-2")).toHaveAttribute("fill", "#6a6f7e");
  });

  it("shows the game name on hover", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    fireEvent.mouseEnter(screen.getByTestId("point-1"));
    expect(screen.getByText("Dungeon of Echoes")).toBeInTheDocument();
  });

  it("calls onSelect when a point is clicked", () => {
    const onSelect = vi.fn();
    render(<GemScatterChart gems={[gemInZone]} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("point-1"));
    expect(onSelect).toHaveBeenCalledWith(gemInZone);
  });

  it("toggles to a table view with the same data", () => {
    render(<GemScatterChart gems={[gemInZone]} />);
    fireEvent.click(screen.getByRole("button", { name: "표로 보기" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Dungeon of Echoes" })).toBeInTheDocument();
  });
});
