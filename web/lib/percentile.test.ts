import { describe, expect, it } from "vitest";

import { bottomPercentileLabel, isHiddenGemZone, topPercentileLabel } from "./percentile";

describe("topPercentileLabel", () => {
  it("floors at 1% instead of showing 0% for the top-ranked game", () => {
    expect(topPercentileLabel(1.0)).toBe(1);
  });

  it("rounds to the nearest percent", () => {
    expect(topPercentileLabel(0.9)).toBe(10);
  });
});

describe("bottomPercentileLabel", () => {
  it("rounds to the nearest percent", () => {
    expect(bottomPercentileLabel(0.2)).toBe(20);
  });
});

describe("isHiddenGemZone", () => {
  it("is true for high quality and low exposure", () => {
    expect(isHiddenGemZone(0.9, 0.1)).toBe(true);
  });

  it("is false for high quality and high exposure", () => {
    expect(isHiddenGemZone(0.9, 0.8)).toBe(false);
  });

  it("is false for low quality and low exposure", () => {
    expect(isHiddenGemZone(0.4, 0.1)).toBe(false);
  });

  it("treats both thresholds as inclusive", () => {
    expect(isHiddenGemZone(0.7, 0.3)).toBe(true);
  });
});
