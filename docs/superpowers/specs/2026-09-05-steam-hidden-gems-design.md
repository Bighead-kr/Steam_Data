# 스팀 저평가 게임 발굴 웹앱 — 설계 문서

- 작성일: 2026-09-05
- 상태: 설계 확정, 구현 계획 대기
- 프로젝트 폴더: `~/Desktop/Develop/Data3`
- 포트폴리오 세 번째 프로젝트. 플래그십 GA4 프로젝트(`~/Desktop/Develop/Data2`)의 코어
  완성 이후 병행 진행.

## 배경

Data3는 원래 사람인 오픈 API 기반 "채용 공고 기술 스택 트래커"로 설계됐다
(`2026-09-04-data-job-market-tracker-design.md` 참고). 그러나 2026-09-05, 사람인
측으로부터 오픈 API가 **개인에게는 발급되지 않는다**는 안내를 메일로 받아 데이터
소스 전제가 무너졌다. 코드베이스에는 `src/tracker/config.py` 수준의 스캐폴딩만
있고 파이프라인 로직은 없어 피벗 비용이 낮았다. 이에 주제를 전면 교체한다.

이전 설계 문서는 삭제하지 않고 보존한다 (피벗 사유와 API 조사 결과 자체가 기록
가치가 있음). 이 문서가 Data3의 현재 유효한 스펙이다.

## 한 줄 정의

Steam 공식 Web API + SteamSpy 데이터로 인디 · 로그라이크 · 시뮬레이션/경영 장르에서
"리뷰 품질은 높은데 노출(소유자 수)이 낮은" 저평가 게임을 발굴해, 장르·태그·예산
조건을 입력하면 랭킹과 판정 근거를 보여주는 웹 서비스.

## 목표와 스코프

### 답하는 질문

1. **핵심** — 장르·태그·예산 조건 안에서 품질 대비 저평가된 게임은 무엇인가.
2. **근거** — 그 게임이 왜 저평가로 판정됐는가 (리뷰 품질 백분위 vs 노출 백분위).
3. **여유 시** — 저평가 게임들의 공통 특징 (가격대, 출시 시기, 태그 조합 패턴).

### 대상 장르/태그

인디(Indie), 로그라이크(Roguelike), 시뮬레이션/경영(Simulation/Management).
SteamSpy `genre`/`tags` 필드로 후보군을 1차로 좁힌다 (예상 규모: 수천~1만 개).

### 명시적으로 스코프 아웃

- 개인 취향 기반 추천(협업 필터링) — 콜드스타트 문제, "발굴"이라는 문제의식과
  다른 방향.
- 매출·수익 예측 — 실매출 데이터가 공개되지 않음. `owners` 추정치로 대체.
- 로그인 / 개인화 / 찜하기 — 세션 단위 조회 도구로 충분.
- 실시간성 — 게임 메타데이터는 자주 바뀌지 않으므로 주 1회 배치로 충분.

## 데이터 소스

| 소스 | 제공 정보 | 인증 |
|---|---|---|
| Steam Web API (`ISteamApps/GetAppList`, `store.steampowered.com/api/appdetails`) | 게임명, 장르, 태그, 가격, 출시일, 리뷰 요약(긍정률·리뷰수), DLC 여부 | 개인 키 (무료, `steamcommunity.com/dev/apikey`에서 즉시 발급 — Domain Name 칸은 `localhost` 입력으로 통과) |
| SteamSpy API (`steamspy.com/api.php`) | 소유자 수 추정 구간, 평균/중앙 플레이타임, 긍정/부정 평가 수 | 불필요 |

### API가 주지 않는 것 / 한계

- 실제 판매량·매출 — `owners`는 SteamSpy의 추정치(구간값)이며 오차가 클 수 있다.
  대시보드에 "추정치이며 정확한 판매량이 아님"을 명시한다.
- 리뷰 수 자체가 어뷰징/봇 영향을 받을 수 있음 — 알려진 한계로 문서화, 별도
  이상치 제거 로직은 이번 스코프에 넣지 않는다.

## 아키텍처

### 파이프라인 (Data3 기존 4단계 원칙 재사용: 단계 분리, 원본 불변, 멱등성)

```
[SteamSpy 후보 목록 (genre/tag 필터)]
      │  주 1회 (GitHub Actions cron)
      ▼
  collector      SteamSpy 후보 + Steam Store API(appdetails) 보강
                 → games_raw 에 원본 JSON 그대로 upsert (멱등)
      ▼
  normalizer     games_raw → games 정제
                 (가격/장르/태그/출시일 파싱, cohort_genre/cohort_year 산출)
      ▼
  scorer         베이지안 보정 품질점수 + 코호트(장르×연도) 내 백분위 정규화
                 → game_scores 적재
      ▼
  [Postgres]  ◄── FastAPI (읽기 전용 API)
      ▼
  [Next.js 웹앱]
```

- **단계 분리**: 각 단계는 앞 단계가 쓴 DB 테이블만 읽는다.
- **원본 불변**: `games_raw.raw_json`은 API 응답을 그대로 보존.
- **멱등성**: 모든 단계가 재실행 안전 (upsert).
- collector만 소스 의존적 — 데이터 소스가 추가돼도(예: Epic, GOG) collector만 바뀐다.

### 배포 토폴로지 (Data3 기존 계획과 동일)

| 구성요소 | 호스팅 | 비용 |
|---|---|---|
| 파이프라인 실행 | GitHub Actions cron (주 1회) | 무료 |
| Postgres | Supabase 무료 티어 | 무료 |
| FastAPI (읽기 전용) | Render 또는 Railway | $0~7/월 |
| Next.js 웹앱 | Vercel | 무료 |

- Actions Secrets: `STEAM_API_KEY`, `DATABASE_URL`.
- Steam Store API에는 공식 rate limit이 없으나 관례상 초당 1건 권장 — 후보 수천
  개 기준 배치 수십 분 소요.

## 데이터 모델

```
games_raw
  app_id        INT PK
  raw_json      JSONB            -- appdetails + steamspy 응답 원본
  fetched_at    TIMESTAMPTZ

games                            -- 정제된 게임
  app_id            INT PK FK
  name              TEXT
  genres            TEXT[]
  tags              TEXT[]
  release_date      DATE
  price_cents       INT NULL     -- 무료/가격 미정 NULL
  is_dlc            BOOLEAN
  review_score_pct  NUMERIC NULL -- Steam 긍정률
  review_count      INT NULL
  owners_low        INT NULL     -- SteamSpy 소유자 추정 하한
  owners_high       INT NULL
  avg_playtime_min  INT NULL
  cohort_genre      TEXT         -- 스코어링용 대표 장르 1개 (우선순위 규칙으로 선정)
  cohort_year       INT          -- 출시연도

game_scores                      -- scorer 단계 산출물
  app_id             INT PK FK
  quality_score      NUMERIC     -- 베이지안 보정 긍정률
  quality_pctile     NUMERIC     -- 코호트(장르×연도) 내 백분위
  exposure_pctile    NUMERIC     -- owners 기준 코호트 내 백분위
  hidden_gem_score   NUMERIC     -- quality_pctile - exposure_pctile
  computed_at        TIMESTAMPTZ

pipeline_runs                    -- 데이터 품질 모니터링 (Data3 기존 패턴)
  run_id             TEXT PK
  started_at         TIMESTAMPTZ
  finished_at        TIMESTAMPTZ NULL
  status             TEXT        -- 'ok' | 'failed'
  games_collected    INT
  games_new          INT
  notes              TEXT NULL
```

### cohort_genre 선정 규칙

우선순위: SteamSpy `genre` 필드의 첫 번째 값 → 없으면 Steam Store API `genres`의
첫 번째 값. 여러 태그를 동시에 가진 게임(예: 인디+로그라이크)도 스코어링용
대표 장르는 하나로 고정해 코호트 정의를 단순하게 유지한다.

## 스코어링 로직

입력: `games.review_score_pct`, `review_count`, `owners_low`, `owners_high`,
`cohort_genre`, `cohort_year`.

1. **베이지안 보정 품질점수** — 리뷰 수가 적은 게임의 극단값(리뷰 5개 100% 긍정 등)을
   방지하기 위해 전체 평균 쪽으로 수축:
   `quality_score = (review_count × review_score_pct + C × m) / (review_count + C)`
   - `m` = 코호트(장르×연도) 전체 평균 긍정률
   - `C` = 보정 강도 상수 (구현 시 데이터로 튜닝, 초기값 예: 코호트 중앙 리뷰수)
2. **코호트 정규화** — `cohort_genre × cohort_year` 파티션 안에서
   `quality_score`와 `owners` 중간값(`(owners_low + owners_high) / 2`)을 각각
   백분위로 변환 (`PERCENT_RANK` 또는 동등 로직).
   - 코호트 표본이 너무 작으면(구현 시 최소 표본 수 정의, 예: 20개 미만) 상위
     카테고리(장르만, 연도 무시)로 fallback.
3. **저평가 점수** — `hidden_gem_score = quality_pctile - exposure_pctile`
   (높을수록 "품질 대비 저평가").

핵심: 점수 산출 근거(백분위 두 값)를 그대로 웹앱 카드 설명 문구로 노출한다
("장르 내 리뷰 품질 상위 10%, 소유자 수는 하위 30%").

## API / 웹앱

### API (FastAPI, 읽기 전용)

- `GET /games/gems?genre=&tag=&max_price=&limit=`
  → `hidden_gem_score` 내림차순 랭킹. 각 항목에 `quality_pctile`,
  `exposure_pctile`, `review_score_pct`, `review_count`, `owners_low/high`,
  `price_cents` 포함.

### 웹앱 (Next.js, 단일 페이지)

- 필터 폼(장르/태그 다중 선택, 최대 예산) → 랭킹 카드 리스트.
- 카드: 게임명, 가격, 판정 근거 문구, 리뷰 긍정률·리뷰수·소유자 추정 구간.
- 선택 상태는 URL 쿼리스트링으로 유지 (Data3 기존 설계 재사용).
- 다크모드·모바일 반응형.

## 테스트 & 데이터 품질

- **단위 테스트 (pytest)**: normalizer(가격/장르/태그 파싱, cohort_genre 선정
  규칙), scorer(베이지안 공식 정확성, 코호트 파티션 백분위 계산, 표본 부족 시
  fallback 로직) — 이 프로젝트의 기술적 핵심이므로 가장 두껍게 검증한다.
- **픽스처**: 손으로 만든 현실적인 appdetails/SteamSpy 응답 샘플 (다양한 리뷰수·
  가격·장르 조합 포함, 극단값 케이스 포함).
- **데이터 품질 모니터링**: 실행마다 `pipeline_runs` 기록 (수집 수, 신규 수,
  실패 여부).
- **FastAPI**: 엔드포인트 통합 테스트 (테스트 DB 시드 → 응답 스냅샷).

## 리스크 & 오픈 이슈

| 리스크 | 대응 |
|---|---|
| SteamSpy 소유자 추정치 부정확 (구간값, 오차 큼) | 대시보드에 "추정치" 명시, 정성적 보조지표로 프레이밍 |
| 코호트 표본 작음 (장르×연도 조합에 게임 수 적음) | 최소 표본 수 미달 시 장르만으로 fallback |
| 리뷰 수가 봇/어뷰징 영향을 받을 수 있음 | 스코프 아웃, 알려진 한계로 문서화 |
| Steam Store API 응답 스키마가 게임마다 들쭉날쭉 (일부 필드 결측) | normalizer에서 NULL 허용 설계, 결측률을 pipeline_runs에 기록 |
| 베이지안 보정 상수 C의 초기값 근거 부족 | Phase A에서 실데이터로 몇 가지 값 비교 후 확정, 근거를 스펙/커밋에 남김 |

## 구현 단계 계획 (개요 — 상세는 writing-plans에서)

### Phase A — 스캐폴딩 · 픽스처 기반 개발

1. `src/tracker` → 도메인에 맞는 패키지명으로 정리 (기존 스캐폴딩 재사용,
   `config.py`는 `STEAM_API_KEY` 등으로 갱신).
2. DB 스키마 + Alembic 마이그레이션 (`games_raw`, `games`, `game_scores`,
   `pipeline_runs`).
3. Steam Store API / SteamSpy 응답 픽스처 작성 (다양한 케이스).
4. normalizer / scorer 구현 + 단위 테스트 (픽스처 대상).
5. FastAPI 엔드포인트 + 통합 테스트 (시드 DB).
6. Next.js 웹앱 (목 데이터 → 픽스처 API).
7. GitHub Actions cron 워크플로 스켈레톤 (더미 키).

### Phase B — 실 API 연동 후

8. collector 구현 + 실데이터 수집 (SteamSpy 후보 목록 + appdetails 보강).
9. 실데이터로 스코어링 로직 검증, 베이지안 상수 C 튜닝.
10. 프로덕션 배포 (Supabase / Render / Vercel), cron 활성화.
11. 두괄식 케이스 스터디 문서 + Notion source of truth 페이지 갱신.

### 코어 완성 기준 (지원 시 보여줄 수 있는 최소선)

- 라이브 URL에서 장르/태그/예산 필터 → 저평가 게임 랭킹이 실데이터로 동작.
- 판정 근거(백분위)가 카드에 명확히 노출됨.
- README + 두괄식 1페이지 (결론 → 방법 → 한계).

## 참고

- 병행 원칙: 지원은 2026-09-15에 시작한다. 이 프로젝트는 지원과 병행하며,
  지원 시작을 미루는 사유가 되지 않는다.
- 이전 설계(사람인 API 기반)는 `2026-09-04-data-job-market-tracker-design.md`에
  보존. 피벗 사유: 사람인 오픈 API는 개인에게 발급되지 않음 (2026-09-05 메일 확인).
