export default function AboutPage() {
  return (
    <main className="mx-auto max-w-[720px] px-6 py-10">
      <a href="/" className="text-ink-secondary text-sm">
        ← 돌아가기
      </a>
      <h1 className="text-ink-primary mt-6 text-2xl font-bold">
        리뷰 품질은 높은데 아무도 모르는 게임을 어떻게 찾나요
      </h1>
      <p className="text-ink-primary mt-4 text-base leading-7">
        리뷰 긍정률이 코호트(같은 장르·같은 출시연도) 평균보다 높으면서, 소유자 추정치는 하위권인
        게임을 저평가로 판정합니다. 리뷰 수가 적어 극단값이 나오는 걸 막기 위해 베이지안 보정을
        거친 뒤, 같은 코호트 안에서 백분위로 비교합니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">데이터 소스</h2>
      <p className="text-ink-secondary mt-2 text-sm leading-6">
        게임 정보와 리뷰 긍정률은 Steam 공식 Web API에서, 소유자 수 추정 구간은 SteamSpy에서
        가져옵니다. 두 소스 모두 매일 배치로 갱신됩니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">한계</h2>
      <ul className="text-ink-secondary mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6">
        <li>owners는 SteamSpy의 추정 구간값이라 실제 판매량과 오차가 있을 수 있습니다.</li>
        <li>리뷰 수 자체가 어뷰징이나 봇의 영향을 받을 수 있으며, 별도 이상치 제거는 하지 않습니다.</li>
        <li>같은 장르·연도 조합의 게임 수가 적으면 장르만으로 비교 범위를 넓힙니다.</li>
      </ul>
    </main>
  );
}
