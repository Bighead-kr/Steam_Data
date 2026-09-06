import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("explains why nothing rendered and what to do next", () => {
    render(<EmptyState />);
    expect(screen.getByText("조건에 맞는 게임이 없습니다")).toBeInTheDocument();
    expect(screen.getByText(/다시 검색해보세요/)).toBeInTheDocument();
  });
});
