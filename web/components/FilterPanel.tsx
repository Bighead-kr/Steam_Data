import type { Filters } from "../lib/types";

const GENRE_OPTIONS = [
  { value: "indie", label: "인디" },
  { value: "simulation", label: "시뮬레이션" },
];

export function FilterPanel({
  filters,
  loading,
  onChange,
  onSubmit,
}: {
  filters: Filters;
  loading: boolean;
  onChange: (filters: Filters) => void;
  onSubmit: () => void;
}) {
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
          {GENRE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        태그
        <input
          type="text"
          value={filters.tag}
          onChange={(e) => onChange({ ...filters, tag: e.target.value })}
          placeholder="Roguelike"
          className="bg-surface-raised text-ink-primary border-border rounded-md border px-3 py-2"
        />
      </label>
      <label className="text-ink-secondary flex flex-col gap-1.5 text-sm">
        최대 예산 (USD)
        <input
          type="number"
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
    </form>
  );
}
