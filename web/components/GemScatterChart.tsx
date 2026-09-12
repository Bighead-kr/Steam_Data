"use client";

import { useState } from "react";

import {
  GEM_ZONE_MAX_EXPOSURE_PCTILE,
  GEM_ZONE_MIN_QUALITY_PCTILE,
  isHiddenGemZone,
} from "../lib/percentile";
import type { Gem } from "../lib/types";

const WIDTH = 520;
const HEIGHT = 400;
// Per-side padding, not one number: the left side has to hold a rotated axis
// title plus tick labels, the bottom the same, and the chart used to have
// neither. A reader could see a purple box labelled "숨은 명작 구간" with no
// way to tell what either axis measured.
const PAD_LEFT = 58;
const PAD_RIGHT = 16;
const PAD_TOP = 16;
const PAD_BOTTOM = 52;
const PLOT_WIDTH = WIDTH - PAD_LEFT - PAD_RIGHT;
const PLOT_HEIGHT = HEIGHT - PAD_TOP - PAD_BOTTOM;
const ACCENT_GEM = "#7c6af0";
const INK_MUTED = "#6a6f7e";
const INK_SECONDARY = "#9ba0af";
const BORDER = "#2e3340";
const TICKS = [0, 0.25, 0.5, 0.75, 1];
// SteamSpy reports owners as a coarse bucket range (e.g. "100,000 ..
// 200,000"), so many games in the same cohort share the exact same
// owners_mid and land on the identical exposure_pctile - without jitter
// they render as a single stack of overlapping dots that reads as a solid
// vertical bar. The jitter spreads ties into a legible cluster; it never
// changes which cohort/zone a point is in, only its on-screen position.
const JITTER_RADIUS = 5;

function toX(exposurePctile: number): number {
  return PAD_LEFT + exposurePctile * PLOT_WIDTH;
}

function toY(qualityPctile: number): number {
  return PAD_TOP + (1 - qualityPctile) * PLOT_HEIGHT;
}

// Deterministic pseudo-random offset in [-JITTER_RADIUS, JITTER_RADIUS],
// seeded by app_id (and an axis-specific seed) so a point's jitter is
// stable across re-renders instead of jumping around on every hover.
function jitter(appId: number, axisSeed: number): number {
  const raw = Math.sin(appId * 12.9898 + axisSeed * 78.233) * 43758.5453;
  const fraction = raw - Math.floor(raw);
  return (fraction - 0.5) * 2 * JITTER_RADIUS;
}

function pointPosition(gem: Gem): { x: number; y: number } {
  const x = toX(gem.exposure_pctile) + jitter(gem.app_id, 1);
  const y = toY(gem.quality_pctile) + jitter(gem.app_id, 2);
  return {
    x: Math.min(WIDTH - PAD_RIGHT, Math.max(PAD_LEFT, x)),
    y: Math.min(HEIGHT - PAD_BOTTOM, Math.max(PAD_TOP, y)),
  };
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
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-ink-primary text-base font-semibold">품질 대비 노출 사분면</h2>
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="text-ink-secondary text-xs underline"
        >
          {showTable ? "차트로 보기" : "표로 보기"}
        </button>
      </div>
      <p className="text-ink-muted mb-3 text-xs leading-5">
        같은 장르·연도 코호트 안에서의 순위입니다. 왼쪽 위 = 리뷰 품질은 상위인데 소유자 수는
        하위인 구간.
      </p>
      {showTable ? (
        <div className="overflow-x-auto">
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
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label="가로축은 노출 백분위(소유자 수), 세로축은 품질 백분위(리뷰)인 산점도. 왼쪽 위가 숨은 명작 구간."
          className="w-full"
        >
          <rect
            x={PAD_LEFT}
            y={PAD_TOP}
            width={GEM_ZONE_MAX_EXPOSURE_PCTILE * PLOT_WIDTH}
            height={(1 - GEM_ZONE_MIN_QUALITY_PCTILE) * PLOT_HEIGHT}
            fill={ACCENT_GEM}
            fillOpacity={0.12}
          />
          <text x={PAD_LEFT + 6} y={PAD_TOP + 15} fill={ACCENT_GEM} fontSize={11}>
            숨은 명작 구간
          </text>

          {TICKS.map((tick) => (
            <g key={`x-${tick}`}>
              <line
                x1={toX(tick)}
                y1={PAD_TOP}
                x2={toX(tick)}
                y2={HEIGHT - PAD_BOTTOM}
                stroke={BORDER}
                strokeOpacity={tick === 0 ? 0 : 0.5}
                strokeDasharray="2 4"
              />
              <text
                x={toX(tick)}
                y={HEIGHT - PAD_BOTTOM + 18}
                fill={INK_MUTED}
                fontSize={10}
                textAnchor="middle"
              >
                {tick * 100}%
              </text>
            </g>
          ))}
          {TICKS.map((tick) => (
            <g key={`y-${tick}`}>
              <line
                x1={PAD_LEFT}
                y1={toY(tick)}
                x2={WIDTH - PAD_RIGHT}
                y2={toY(tick)}
                stroke={BORDER}
                strokeOpacity={tick === 0 ? 0 : 0.5}
                strokeDasharray="2 4"
              />
              <text
                x={PAD_LEFT - 8}
                y={toY(tick) + 3}
                fill={INK_MUTED}
                fontSize={10}
                textAnchor="end"
              >
                {tick * 100}%
              </text>
            </g>
          ))}

          <line
            x1={PAD_LEFT}
            y1={HEIGHT - PAD_BOTTOM}
            x2={WIDTH - PAD_RIGHT}
            y2={HEIGHT - PAD_BOTTOM}
            stroke={BORDER}
          />
          <line x1={PAD_LEFT} y1={PAD_TOP} x2={PAD_LEFT} y2={HEIGHT - PAD_BOTTOM} stroke={BORDER} />

          <text
            x={PAD_LEFT + PLOT_WIDTH / 2}
            y={HEIGHT - 10}
            fill={INK_SECONDARY}
            fontSize={11}
            textAnchor="middle"
          >
            노출 백분위 (소유자 수) →
          </text>
          <text
            x={-(PAD_TOP + PLOT_HEIGHT / 2)}
            y={14}
            fill={INK_SECONDARY}
            fontSize={11}
            textAnchor="middle"
            transform="rotate(-90)"
          >
            품질 백분위 (리뷰) →
          </text>

          {gems.map((gem) => {
            const isGem = isHiddenGemZone(gem.quality_pctile, gem.exposure_pctile);
            const { x, y } = pointPosition(gem);
            return (
              <circle
                key={gem.app_id}
                data-testid={`point-${gem.app_id}`}
                cx={x}
                cy={y}
                r={5}
                fill={isGem ? ACCENT_GEM : INK_MUTED}
                fillOpacity={isGem ? 1 : 0.75}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredId(gem.app_id)}
                onMouseLeave={() => setHoveredId((id) => (id === gem.app_id ? null : id))}
                onClick={() => onSelect?.(gem)}
              />
            );
          })}
          {hovered &&
            (() => {
              const { x, y } = pointPosition(hovered);
              // Flip the label to the left of the point near the right edge
              // so long names don't run off the plot.
              const flip = x > PAD_LEFT + PLOT_WIDTH * 0.66;
              return (
                <text
                  x={flip ? x - 8 : x + 8}
                  y={y - 8}
                  fill="#edeef2"
                  fontSize={11}
                  textAnchor={flip ? "end" : "start"}
                >
                  {hovered.name}
                </text>
              );
            })()}
        </svg>
      )}
    </div>
  );
}
