import type { Facet, Filters } from "../lib/types";

const GENRE_LABELS: Record<string, string> = {
  indie: "인디",
  simulation: "시뮬레이션",
  action: "액션",
  adventure: "어드벤처",
  rpg: "RPG",
  strategy: "전략",
  casual: "캐주얼",
  unknown: "분류 없음",
};

function genreLabel(value: string): string {
  return GENRE_LABELS[value] ?? value;
}

export function FilterPanel({
  filters,
  genres,
  tags,
  loading,
  onChange,
  onSubmit,
}: {
  filters: Filters;
  genres: Facet[];
  tags: Facet[];
  loading: boolean;
  onChange: (filters: Filters) => void;
  onSubmit: () => void;
}) {
  // Until /genres answers, the only genre we can honestly offer is the one
  // already selected - inventing a list is how the hardcoded dropdown came
  // to advertise a genre with one game behind it.
  const genreOptions = genres.length > 0 ? genres : [{ value: filters.genre, count: 0 }];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="bg-surface border-border flex flex-col gap-4 rounded-lg border p-5"
    >
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        장르
        <select
          value={filters.genre}
          onChange={(e) => onChange({ ...filters, genre: e.target.value })}
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        >
          {genreOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {genreLabel(option.value)}
              {option.count > 0 ? ` (${option.count.toLocaleString()})` : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        태그
        {/* A text input here was a spelling test the user loses: SteamSpy
            tags are exact-cased strings ("Roguelike", "Co-op"), and any near
            miss returned zero results with no hint why. */}
        <select
          value={filters.tag}
          onChange={(e) => onChange({ ...filters, tag: e.target.value })}
          disabled={tags.length === 0}
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2 disabled:opacity-50"
        >
          <option value="">전체</option>
          {tags.map((tag) => (
            <option key={tag.value} value={tag.value}>
              {tag.value} ({tag.count.toLocaleString()})
            </option>
          ))}
        </select>
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        최대 예산 (USD)
        <input
          type="number"
          min={0}
          value={filters.maxPrice}
          onChange={(e) => onChange({ ...filters, maxPrice: e.target.value })}
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        />
      </label>
      <button
        type="submit"
        disabled={loading}
        className="bg-accent-gem rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {loading ? "검색 중..." : "검색"}
      </button>
      <p className="text-ink-muted text-xs leading-5">
        가격 정보가 없는 게임은 예산 필터를 적용하면 제외됩니다.
      </p>
    </form>
  );
}
