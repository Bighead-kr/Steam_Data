import { Suspense } from "react";

import { ExplorerSkeleton } from "../components/ExplorerSkeleton";
import { GemExplorer } from "../components/GemExplorer";

// A server component on purpose. Everything that reads the URL query string
// (and so opts out of static rendering) lives inside GemExplorer, behind the
// Suspense boundary below - the heading and the explanation render on the
// server and are in the HTML before any JavaScript runs. When the whole page
// was one "use client" component wrapped in <Suspense fallback={null}>, Next
// bailed the entire route out to client rendering and shipped an empty
// <body>.
export default function HomePage() {
  return (
    <main className="mx-auto max-w-[1120px] px-6 py-10">
      <header className="flex items-center justify-between">
        <span className="text-ink-primary text-sm font-semibold">Steam Hidden Gems</span>
        <a href="/about" className="text-ink-secondary text-sm">
          방법론
        </a>
      </header>
      <h1 className="text-ink-primary mt-8 text-[28px] font-bold sm:text-[40px]">
        리뷰는 좋은데 아무도 모르는 게임을 찾습니다
      </h1>
      <p className="text-ink-secondary mt-2 text-sm">
        장르·태그·예산을 고르면 품질 대비 저평가된 게임을 백분위 근거와 함께 보여줍니다.
      </p>
      <Suspense fallback={<ExplorerSkeleton />}>
        <GemExplorer />
      </Suspense>
    </main>
  );
}
