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
        거친 뒤, 같은 코호트 안에서 백분위로 비교합니다. 품질 상위 30% 이내이면서 노출 하위 30%
        이내인 게임에 &ldquo;숨은 명작&rdquo; 배지가 붙습니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">데이터 소스</h2>
      <p className="text-ink-secondary mt-2 text-sm leading-6">
        게임 이름·가격·출시일·장르는 Steam Store의 appdetails API에서, 리뷰 긍정/부정 수와 소유자
        추정 구간, 태그는 SteamSpy에서 가져옵니다. 즉 긍정률은 Steam이 화면에 표시하는 리뷰 점수가
        아니라 SteamSpy가 집계한 긍정/부정 수로 직접 계산한 값입니다. 매일 배치로 갱신합니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">코호트를 나누는 기준</h2>
      <p className="text-ink-secondary mt-2 text-sm leading-6">
        코호트의 장르는 해당 게임을 수집해 온 SteamSpy 장르 목록(현재 Simulation, Indie)을
        따릅니다. 두 목록에 모두 있는 게임은 더 구체적인 쪽(Simulation)으로 묶습니다. Steam이
        게임마다 주는 장르 배열의 첫 값은 장르 ID 순서라 Action·Adventure에 쏠리기 때문에 쓰지
        않습니다.
      </p>
      <h2 className="text-ink-primary mt-8 text-lg font-semibold">한계</h2>
      <ul className="text-ink-secondary mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6">
        <li>owners는 SteamSpy의 추정 구간값이라 실제 판매량과 오차가 있을 수 있습니다.</li>
        <li>
          그 추정값은 구간(예: 20,000 ~ 50,000)이라 같은 구간에 속한 게임끼리는 노출 백분위가
          동률이 됩니다. 산점도에서 점들이 세로줄로 뭉쳐 보이는 이유입니다.
        </li>
        <li>리뷰 수 자체가 어뷰징이나 봇의 영향을 받을 수 있으며, 별도 이상치 제거는 하지 않습니다.</li>
        <li>같은 장르·연도 조합의 게임 수가 적으면 장르만으로 비교 범위를 넓히고, 그래도 모자라면 점수를 매기지 않습니다.</li>
        <li>DLC·사운드트랙은 본편에 얹힌 수치라 코호트와 순위에서 제외합니다.</li>
        <li>
          가격 정보가 없는 게임(Steam이 price_overview를 주지 않는 경우)은 예산 필터를 걸면
          제외됩니다.
        </li>
        <li>
          백분위는 자기 자신을 포함해 계산하므로 코호트 1위는 항상 상위 1%로 표시됩니다.
        </li>
      </ul>
    </main>
  );
}
