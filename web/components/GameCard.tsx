export type Gem = {
  app_id: number;
  name: string;
  price_cents: number | null;
  genres: string[];
  tags: string[];
  review_score_pct: number | null;
  review_count: number | null;
  owners_low: number | null;
  owners_high: number | null;
  quality_pctile: number;
  exposure_pctile: number;
  hidden_gem_score: number;
};

function formatPrice(cents: number | null): string {
  if (cents === null) return "가격 정보 없음";
  if (cents === 0) return "무료";
  return `$${(cents / 100).toFixed(2)}`;
}

export function GameCard({ gem }: { gem: Gem }) {
  const qualityTopPct = Math.round((1 - gem.quality_pctile) * 100);
  const exposureBottomPct = Math.round(gem.exposure_pctile * 100);

  return (
    <article>
      <h3>{gem.name}</h3>
      <p>{formatPrice(gem.price_cents)}</p>
      <p>
        장르 내 리뷰 품질 상위 {qualityTopPct}%, 소유자 수는 하위 {exposureBottomPct}%
      </p>
      <p>
        긍정률 {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개 리뷰)
      </p>
    </article>
  );
}
