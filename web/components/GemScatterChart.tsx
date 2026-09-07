"use client";

import { useState } from "react";

import {
  GEM_ZONE_MAX_EXPOSURE_PCTILE,
  GEM_ZONE_MIN_QUALITY_PCTILE,
  isHiddenGemZone,
} from "../lib/percentile";
import type { Gem } from "../lib/types";

const WIDTH = 480;
const HEIGHT = 360;
const PADDING = 32;
const PLOT_WIDTH = WIDTH - PADDING * 2;
const PLOT_HEIGHT = HEIGHT - PADDING * 2;
const ACCENT_GEM = "#7c6af0";
const INK_MUTED = "#6a6f7e";

function toX(exposurePctile: number): number {
  return PADDING + exposurePctile * PLOT_WIDTH;
}

function toY(qualityPctile: number): number {
  return PADDING + (1 - qualityPctile) * PLOT_HEIGHT;
}

export function GemScatterChart({
  gems,
  onSelect,
}: {
  gems: Gem[];
  onSelect?: (gem: Gem) => void;
}) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const hovered = gems.find((g) => g.app_id === hoveredId) ?? null;

  return (
    <div className="bg-surface border-border rounded-lg border p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-ink-primary text-base font-semibold">품질 대비 노출 사분면</h2>
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="text-ink-secondary text-xs underline"
        >
          {showTable ? "차트로 보기" : "표로 보기"}
        </button>
      </div>
      {showTable ? (
        <table className="text-ink-secondary w-full text-left text-sm">
          <thead>
            <tr>
              <th className="pb-2">게임</th>
              <th className="pb-2">품질 백분위</th>
              <th className="pb-2">노출 백분위</th>
            </tr>
          </thead>
          <tbody>
            {gems.map((gem) => (
              <tr key={gem.app_id} className="border-border border-t">
                <td className="py-1.5">{gem.name}</td>
                <td className="py-1.5 tabular-nums">{Math.round(gem.quality_pctile * 100)}%</td>
                <td className="py-1.5 tabular-nums">{Math.round(gem.exposure_pctile * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label="품질 백분위 대 노출 백분위 산점도"
          className="w-full"
        >
          <rect
            x={PADDING}
            y={PADDING}
            width={GEM_ZONE_MAX_EXPOSURE_PCTILE * PLOT_WIDTH}
            height={(1 - GEM_ZONE_MIN_QUALITY_PCTILE) * PLOT_HEIGHT}
            fill={ACCENT_GEM}
            fillOpacity={0.12}
          />
          <text x={PADDING + 4} y={PADDING + 14} fill={ACCENT_GEM} fontSize={10}>
            숨은 명작 구간
          </text>
          <line
            x1={PADDING}
            y1={HEIGHT - PADDING}
            x2={WIDTH - PADDING}
            y2={HEIGHT - PADDING}
            stroke="#2e3340"
          />
          <line x1={PADDING} y1={PADDING} x2={PADDING} y2={HEIGHT - PADDING} stroke="#2e3340" />
          {gems.map((gem) => {
            const isGem = isHiddenGemZone(gem.quality_pctile, gem.exposure_pctile);
            return (
              <circle
                key={gem.app_id}
                data-testid={`point-${gem.app_id}`}
                cx={toX(gem.exposure_pctile)}
                cy={toY(gem.quality_pctile)}
                r={5}
                fill={isGem ? ACCENT_GEM : INK_MUTED}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredId(gem.app_id)}
                onMouseLeave={() => setHoveredId((id) => (id === gem.app_id ? null : id))}
                onClick={() => onSelect?.(gem)}
              />
            );
          })}
          {hovered && (
            <text
              x={toX(hovered.exposure_pctile) + 8}
              y={toY(hovered.quality_pctile) - 8}
              fill="#edeef2"
              fontSize={11}
            >
              {hovered.name}
            </text>
          )}
        </svg>
      )}
    </div>
  );
}
