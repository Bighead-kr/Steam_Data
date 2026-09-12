/** Placeholder with the same shape as the explorer.
 *
 * This is the Suspense fallback for the part of the page that reads the URL
 * query string. It used to be `null`, which meant the server sent a body
 * containing nothing at all - a visitor arriving while the API was cold
 * stared at a blank white page with no title, no filters and no explanation
 * until the JS bundle and the first response both landed. */
export function ExplorerSkeleton() {
  return (
    <div className="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]" aria-hidden="true">
      <div className="bg-surface border-border h-[320px] animate-pulse rounded-lg border" />
      <div className="bg-surface border-border h-[420px] animate-pulse rounded-lg border" />
    </div>
  );
}
