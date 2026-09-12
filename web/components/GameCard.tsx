import { bottomPercentileLabel, isHiddenGemZone, topPercentileLabel } from "../lib/percentile";
import { steamStoreUrl } from "../lib/steam";
import type { Gem } from "../lib/types";
import { ScoreBadge } from "./ScoreBadge";

export type { Gem };

function formatPrice(cents: number | null): string {
  if (cents === null) return "가격 정보 없음";
  if (cents === 0) return "무료";
  return `$${(cents / 100).toFixed(2)}`;
}

export function GameCard({ gem, onSelect }: { gem: Gem; onSelect?: (gem: Gem) => void }) {
  const qualityTopPct = topPercentileLabel(gem.quality_pctile);
  const exposureBottomPct = bottomPercentileLabel(gem.exposure_pctile);
  const isGem = isHiddenGemZone(gem.quality_pctile, gem.exposure_pctile);

  return (
    // A self-contained bordered card rather than a row separated by a
    // bottom border: in a 3-column grid the borders sat at different heights
    // per column whenever one title wrapped to two lines.
    <article className="border-border bg-surface hover:bg-surface-raised flex flex-col rounded-lg border p-4 transition-colors">
      <div className="flex items-start justify-between gap-3">
        {/* A real button, so the card opens by keyboard too - it used to be
            an <article onClick>, reachable only with a mouse. */}
        <h3 className="text-ink-primary text-base font-semibold">
          <button
            type="button"
            onClick={() => onSelect?.(gem)}
            className="text-left hover:underline"
          >
            {gem.name}
          </button>
        </h3>
        {isGem && <ScoreBadge label="숨은 명작" tone="gem" />}
      </div>
      <p className="text-ink-secondary mt-1 text-sm tabular-nums">{formatPrice(gem.price_cents)}</p>
      <p className="text-ink-secondary mt-2 text-sm">
        장르 내 리뷰 품질 상위 {qualityTopPct}%, 소유자 수는 하위 {exposureBottomPct}%
      </p>
      <p className="text-ink-muted mt-1 text-sm tabular-nums">
        긍정률 {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개 리뷰)
      </p>
      {gem.tags.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {gem.tags.slice(0, 3).map((tag) => (
            <li
              key={tag}
              className="bg-surface-raised text-ink-secondary rounded-full px-2 py-0.5 text-xs"
            >
              {tag}
            </li>
          ))}
        </ul>
      )}
      {/* The point of the whole site is to send you to a game you hadn't
          heard of; until now there was no way to reach one. */}
      <a
        href={steamStoreUrl(gem.app_id)}
        target="_blank"
        rel="noopener noreferrer"
        className="text-accent-gem mt-3 inline-block text-sm hover:underline"
      >
        Steam 상점에서 보기 ↗
      </a>
    </article>
  );
}
