import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FilterPanel } from "./FilterPanel";

const baseFilters = { genre: "indie", tag: "", maxPrice: "" };

describe("FilterPanel", () => {
  it("calls onChange with the updated genre", () => {
    const onChange = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={onChange} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("장르"), { target: { value: "simulation" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, genre: "simulation" });
  });

  it("calls onChange with the updated tag", () => {
    const onChange = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={onChange} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("태그"), { target: { value: "Roguelike" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, tag: "Roguelike" });
  });

  it("calls onSubmit when the form is submitted", () => {
    const onSubmit = vi.fn();
    render(<FilterPanel filters={baseFilters} loading={false} onChange={vi.fn()} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "검색" }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("disables the submit button while loading", () => {
    render(<FilterPanel filters={baseFilters} loading={true} onChange={vi.fn()} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "검색 중..." })).toBeDisabled();
  });
});
