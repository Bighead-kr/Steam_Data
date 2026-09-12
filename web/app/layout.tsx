import type { Metadata } from "next";

import "./globals.css";

// Without this the app shipped with no <title> at all: the browser tab read
// "steam-hidden-gems-web-three.vercel.app" and a shared link previewed as
// nothing.
export const metadata: Metadata = {
  title: "Steam Hidden Gems — 리뷰는 좋은데 아무도 모르는 게임",
  description:
    "Steam Store와 SteamSpy 데이터로, 같은 장르·연도 게임들 사이에서 리뷰 품질은 상위권인데 소유자 수는 하위권인 저평가 게임을 백분위 근거와 함께 찾아줍니다.",
  openGraph: {
    title: "Steam Hidden Gems",
    description: "리뷰 품질 상위, 노출 하위. 저평가된 스팀 게임을 백분위로 발굴합니다.",
    type: "website",
    locale: "ko_KR",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
