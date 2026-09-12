export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="border-border rounded-lg border border-dashed py-16 text-center"
    >
      <p className="text-ink-primary text-base font-medium">결과를 불러오지 못했습니다</p>
      <p className="text-ink-secondary mt-1 text-sm">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="bg-surface-raised text-ink-primary border-border mt-4 rounded-md border px-4 py-2 text-sm"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
