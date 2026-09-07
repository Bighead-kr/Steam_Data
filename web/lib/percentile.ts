// percentile_rank is inclusive-of-self, so the #1 ranked game in any
// cohort always has quality_pctile === 1.0; without the floor that would
// render as "상위 0%" for the single most important result.
export function topPercentileLabel(pctile: number): number {
  return Math.max(1, Math.round((1 - pctile) * 100));
}

export function bottomPercentileLabel(pctile: number): number {
  return Math.round(pctile * 100);
}

export const GEM_ZONE_MIN_QUALITY_PCTILE = 0.7;
export const GEM_ZONE_MAX_EXPOSURE_PCTILE = 0.3;

export function isHiddenGemZone(qualityPctile: number, exposurePctile: number): boolean {
  return (
    qualityPctile >= GEM_ZONE_MIN_QUALITY_PCTILE &&
    exposurePctile <= GEM_ZONE_MAX_EXPOSURE_PCTILE
  );
}
