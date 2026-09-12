export function EmptyState() {
  return (
    <div className="border-border rounded-lg border border-dashed py-16 text-center">
      <p className="text-ink-primary text-base font-medium">조건에 맞는 게임이 없습니다</p>
      <p className="text-ink-secondary mt-1 text-sm">
        태그를 &ldquo;전체&rdquo;로 두거나 예산을 늘려서 다시 검색해보세요.
      </p>
    </div>
  );
}
