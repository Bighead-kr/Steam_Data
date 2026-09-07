import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AboutPage from "./page";

describe("AboutPage", () => {
  it("leads with the conclusion: what counts as underrated", () => {
    render(<AboutPage />);
    expect(
      screen.getByText("리뷰 품질은 높은데 아무도 모르는 게임을 어떻게 찾나요")
    ).toBeInTheDocument();
  });

  it("documents a known limitation of the owners estimate", () => {
    render(<AboutPage />);
    expect(screen.getByText(/SteamSpy의 추정 구간값/)).toBeInTheDocument();
  });

  it("links back to the home page", () => {
    render(<AboutPage />);
    expect(screen.getByRole("link", { name: /돌아가기/ })).toHaveAttribute("href", "/");
  });
});
