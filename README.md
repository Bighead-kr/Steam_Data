# 스팀 저평가 게임 발굴 웹앱

Steam 공식 Web API + SteamSpy 데이터로 인디 · 로그라이크 · 시뮬레이션/경영 장르에서 "리뷰 품질은 높은데 노출(소유자 수)이 낮은" 저평가 게임을 발굴해, 장르·태그·예산 조건을 입력하면 랭킹과 판정 근거를 보여주는 웹 서비스.

> 이 프로젝트는 원래 사람인 오픈 API 기반 채용시장 트래커였으나, 사람인 API가
> 개인에게는 발급되지 않아(2026-09-05 확인) 주제를 교체했다. 경위는
> [이전 설계 문서](docs/superpowers/specs/2026-09-04-data-job-market-tracker-design.md)
> 참고.

## 로컬 실행

1. PostgreSQL 시작:
   ```bash
   docker compose up -d
   ```

2. 의존성 설치:
   ```bash
   pip install -e ".[dev]"
   ```

3. 스키마 마이그레이션:
   ```bash
   alembic upgrade head
   ```

4. 테스트 실행:
   ```bash
   pytest
   ```

## API 서버

FastAPI 개발 서버 실행:

```bash
uvicorn tracker.api.app:app --reload
```

`GET /games/gems`가 핵심 엔드포인트로, `Game`과 `GameScore`를 조인해
`hidden_gem_score` 내림차순으로 정렬한 결과를 반환한다. `genre`, `tag`,
`max_price_cents`, `limit`(1~200) 쿼리 파라미터로 필터링할 수 있으며,
필터·정렬·개수 제한은 전부 SQL에서 처리된다. DLC는 제외된다.

`GET /genres`와 `GET /tags?genre=...`는 웹앱의 필터 선택지를 실제 데이터에서
만들어 준다(`{value, count}` 목록). 하드코딩된 목록이 데이터와 어긋나
조용히 0건을 반환하던 문제를 막기 위한 것이다.

## 파이프라인 실행

```bash
python scripts/run_pipeline.py
```

Steam/SteamSpy 수집(`collect_games`) → 정규화(`run_normalizer`) →
점수 계산(`run_scorer`) → `pipeline_runs`에 실행 기록 저장까지 한 번에
수행한다. `.github/workflows/pipeline.yml`이 이 스크립트를 주기적으로(또는
수동으로) 실행한다.

### 장르와 태그

수집 대상 장르는 `tracker.config.TARGET_GENRES`(현재 `["Simulation", "Indie"]`,
구체적인 순서대로). 게임을 처음 발견한 SteamSpy 장르 목록이 그대로
`cohort_genre`가 되며, Steam appdetails의 `genres[0]`은 쓰지 않는다 — 그 배열은
장르 ID 순이라 Action·Adventure로 쏠린다.

`roguelike`, `management`는 SteamSpy에 장르로 존재하지 않아(요청 시 `{}` 반환)
목록에서 뺐다. 둘 다 Steam **태그**이므로 태그 필터로 찾는다.

### 과거 데이터 보정

수집기가 태그와 `source_genre`를 저장하기 전에 모아둔 `games_raw` 행은
아래 스크립트로 보정한다. 두 단계 모두 중단 후 재개해도 안전하다.

```bash
python scripts/backfill_steamspy.py --phase source-genre   # SteamSpy 호출 2번, 수 초
python scripts/backfill_steamspy.py --phase tags           # 게임당 1회, 1req/sec
```

## 웹앱 (`web/`)

```bash
cd web
npm install
npm run dev
```

Next.js(App Router) + Tailwind CSS로 만든 검색 UI로, `NEXT_PUBLIC_API_BASE_URL`
(기본값 `http://localhost:8000`)로 FastAPI 서버에 요청해 결과를 렌더링한다.
필터 상태는 URL 쿼리스트링에 유지된다.

- `/` — 필터(장르/태그/예산), 품질·노출 백분위 사분면 산점도, 랭킹 카드 그리드.
  카드 제목이나 산점도 점을 클릭하면 점수 근거를 보여주는 상세 모달이 열리고,
  카드·모달 모두 Steam 상점으로 링크된다. 헤더와 제목은 서버에서 렌더링되고,
  URL 쿼리를 읽는 탐색 UI만 Suspense 경계 안에서 클라이언트 렌더링된다.
- `/about` — 스코어링 로직·데이터 소스·한계를 설명하는 방법론 페이지.

디자인 토큰(`web/app/globals.css`)과 컴포넌트 인벤토리는
[웹앱 디자인 시스템 설계 문서](docs/superpowers/specs/2026-09-06-webapp-design-system-design.md)에
정리돼 있다.

테스트:

```bash
cd web
npm test
```

## 스키마 변경 규칙

- `src/tracker/models.py`에서 SQLAlchemy ORM 정의 변경 후, 반드시 Alembic 마이그레이션도 함께 생성하세요.
- `alembic revision --autogenerate -m "설명"` 후 검수 및 실행.

## 스펙 문서

[스팀 저평가 게임 발굴 웹앱 — 설계 문서](docs/superpowers/specs/2026-09-05-steam-hidden-gems-design.md)
