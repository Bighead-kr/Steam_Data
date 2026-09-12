import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FilterPanel } from "./FilterPanel";

const baseFilters = { genre: "indie", tag: "", maxPrice: "" };
const genres = [
  { value: "indie", count: 1370 },
  { value: "simulation", count: 820 },
];
const tags = [
  { value: "Roguelike", count: 240 },
  { value: "Management", count: 96 },
];

function renderPanel(props: Partial<Parameters<typeof FilterPanel>[0]> = {}) {
  return render(
    <FilterPanel
      filters={baseFilters}
      genres={genres}
      tags={tags}
      loading={false}
      onChange={vi.fn()}
      onSubmit={vi.fn()}
      {...props}
    />
  );
}

describe("FilterPanel", () => {
  it("calls onChange with the updated genre", () => {
    const onChange = vi.fn();
    renderPanel({ onChange });
    fireEvent.change(screen.getByLabelText("장르"), { target: { value: "simulation" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, genre: "simulation" });
  });

  it("calls onChange with the updated tag", () => {
    const onChange = vi.fn();
    renderPanel({ onChange });
    fireEvent.change(screen.getByLabelText("태그"), { target: { value: "Roguelike" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, tag: "Roguelike" });
  });

  it("offers the genres the API reports, with their counts", () => {
    renderPanel();
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toContain("인디 (1,370)");
    expect(options).toContain("시뮬레이션 (820)");
  });

  it("offers real tag values instead of a free-text box", () => {
    /** The tag filter used to be a text input, which meant typing SteamSpy's
     * exact casing from memory; every near miss returned zero results. */
    renderPanel();
    expect(screen.getByLabelText("태그").tagName).toBe("SELECT");
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toContain("Roguelike (240)");
  });

  it("disables the tag select when the genre has no tags yet", () => {
    renderPanel({ tags: [] });
    expect(screen.getByLabelText("태그")).toBeDisabled();
  });

  it("falls back to the current genre when the facet request hasn't answered", () => {
    renderPanel({ genres: [] });
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toContain("인디");
  });

  it("calls onSubmit when the form is submitted", () => {
    const onSubmit = vi.fn();
    renderPanel({ onSubmit });
    fireEvent.click(screen.getByRole("button", { name: "검색" }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("disables the submit button while loading", () => {
    renderPanel({ loading: true });
    expect(screen.getByRole("button", { name: "검색 중..." })).toBeDisabled();
  });
});
