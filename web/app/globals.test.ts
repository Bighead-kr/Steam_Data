import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("./globals.css", import.meta.url), "utf-8");

describe("design tokens", () => {
  it("loads Pretendard before Tailwind so the font is available to every utility", () => {
    const pretendardIndex = css.indexOf('@import "pretendard');
    const tailwindIndex = css.indexOf('@import "tailwindcss"');
    expect(pretendardIndex).toBeGreaterThanOrEqual(0);
    expect(tailwindIndex).toBeGreaterThan(pretendardIndex);
  });

  it("defines the accent-gem token used by ScoreBadge and the scatter chart", () => {
    expect(css).toContain("--color-accent-gem: #7c6af0");
  });

  it("defines the void background and primary ink tokens", () => {
    expect(css).toContain("--color-bg-void: #12141a");
    expect(css).toContain("--color-ink-primary: #edeef2");
  });

  it("sets Pretendard as the sans font stack", () => {
    expect(css).toContain('--font-sans: "Pretendard"');
  });
});
