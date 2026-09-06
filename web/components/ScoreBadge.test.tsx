import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreBadge } from "./ScoreBadge";

describe("ScoreBadge", () => {
  it("renders the label text", () => {
    render(<ScoreBadge label="숨은 명작" />);
    expect(screen.getByText("숨은 명작")).toBeInTheDocument();
  });

  it("applies the gem tone class when tone is gem", () => {
    render(<ScoreBadge label="숨은 명작" tone="gem" />);
    expect(screen.getByText("숨은 명작")).toHaveClass("text-accent-gem");
  });

  it("applies the neutral tone class by default", () => {
    render(<ScoreBadge label="정보" />);
    expect(screen.getByText("정보")).toHaveClass("text-ink-secondary");
  });
});
