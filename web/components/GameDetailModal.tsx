"use client";

import { useEffect } from "react";

import { bottomPercentileLabel, topPercentileLabel } from "../lib/percentile";
import type { Gem } from "../lib/types";

export function GameDetailModal({ gem, onClose }: { gem: Gem; onClose: () => void }) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const qualityTopPct = topPercentileLabel(gem.quality_pctile);
  const exposureBottomPct = bottomPercentileLabel(gem.exposure_pctile);

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={gem.name}
        onClick={(e) => e.stopPropagation()}
        className="bg-surface-raised border-border max-h-[80vh] w-full max-w-md overflow-y-auto rounded-lg border p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-ink-primary text-lg font-semibold">{gem.name}</h2>
          <button type="button" onClick={onClose} aria-label="닫기" className="text-ink-secondary text-sm">
            닫기
          </button>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-ink-secondary">품질 백분위</dt>
          <dd className="text-ink-primary tabular-nums">상위 {qualityTopPct}%</dd>
          <dt className="text-ink-secondary">노출 백분위</dt>
          <dd className="text-ink-primary tabular-nums">하위 {exposureBottomPct}%</dd>
          <dt className="text-ink-secondary">긍정률</dt>
          <dd className="text-ink-primary tabular-nums">
            {gem.review_score_pct?.toFixed(1) ?? "N/A"}% ({gem.review_count ?? 0}개)
          </dd>
        </dl>
        <p className="text-ink-secondary mt-4 text-sm">
          장르 내 리뷰 품질은 상위 {qualityTopPct}%인데, 소유자 수는 하위 {exposureBottomPct}%에 그쳐
          저평가로 판정됐습니다.
        </p>
        {gem.tags.length > 0 && (
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {gem.tags.map((tag) => (
              <li key={tag} className="bg-surface text-ink-secondary rounded-full px-2.5 py-1 text-xs">
                {tag}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
