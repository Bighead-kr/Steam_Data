type Tone = "gem" | "neutral";

export function ScoreBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  const toneClasses =
    tone === "gem" ? "bg-accent-gem/20 text-accent-gem" : "bg-surface-raised text-ink-secondary";

  return (
    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses}`}>
      {label}
    </span>
  );
}
