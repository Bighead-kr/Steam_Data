import { bottomPercentileLabel, isHiddenGemZone, topPercentileLabel } from "../lib/percentile";
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
    <article
      onClick={() => onSelect?.(gem)}
      className="border-border hover:bg-surface-raised cursor-pointer border-b py-4 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-ink-primary text-base font-semibold">{gem.name}</h3>
        {isGem && <ScoreBadge label="숨은 명작" tone="gem" />}
      </div>
      <p className="text-ink-secondary mt-1 text-sm tabular-nums">{formatPrice(gem.price_cents)}</p>
      <p className="text-ink-secondary mt-2 text-sm">
        장르 내 리뷰 품질 상위 {qualityTopPct}%, 소유자 수는 하위 {exposureBottomPct}%
      </p>
      <p className="text-ink-muted mt-1 text-sm tabular-nums">
        긍정률 {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개 리뷰)
      </p>
    </article>
  );
}
