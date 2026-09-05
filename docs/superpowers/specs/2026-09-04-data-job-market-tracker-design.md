# 한국 데이터 직군 채용시장 트래커 — 설계 문서

> **[2026-09-05] 폐기됨.** 사람인 오픈 API는 개인에게 발급되지 않는다는 안내를
> 메일로 확인해 데이터 소스 전제가 무너져 주제를 교체했다. 현재 유효한 스펙은
> [`2026-09-05-steam-hidden-gems-design.md`](2026-09-05-steam-hidden-gems-design.md).
> 이 문서는 피벗 사유·API 조사 결과 기록용으로 보존한다.

- 작성일: 2026-09-04
- 상태: **폐기 (2026-09-05)** — 아래 내용은 역사적 기록
- 프로젝트 폴더: `~/Desktop/Develop/Data3`
- 포트폴리오 3번째 프로젝트. 플래그십 GA4 프로젝트(`~/Desktop/Develop/Data2`)의 코어 완성 이후 병행 진행.

## 배경

이 프로젝트는 2026-08-24에 "채용 공고 기술 스택 트래킹"이라는 이름으로 한 번
시작됐다가(`~/Desktop/Develop/Data1`, GitHub `Bighead-kr/Data1`), 요양시설 입지
분석 프로젝트에 폴더·저장소가 덮이면서 중단됐다. 당시 만든 자산은 사람인 오픈 API
클라이언트 코드와 파이프라인 폴더 구조 설계다. 이번에는 별도 폴더(`Data3`)에서
라이브 웹 서비스로 다시 세운다.

동기: 관심 회사·직무에 인턴 지원을 반복했으나 매번 서류에서 탈락했고, 무엇이
부족한지 데이터가 아니라 감으로만 짐작하던 상황. 시장이 실제로 무엇을 요구하는지
직접 수집·분석해 지원 전략과 학습 우선순위를 데이터로 세우는 것이 출발점이다.

## 한 줄 정의

사람인 오픈 API로 한국 데이터 직군 채용 공고를 매일 수집해, 요구 역량의 시계열
변화 · 신입/경력 스킬 갭 · 개인 역량 갭을 보여주는 라이브 웹 서비스.

## 목표와 스코프

### 답하는 질문

1. **트렌드** — 지난 기간 동안 각 스킬의 공고 언급률이 어떻게 변했나. 새로 등장한
   스킬은 무엇인가.
2. **신입 vs 경력 스킬 갭** — 어떤 스킬이 신입에게도 요구되는 진입장벽이고, 어떤
   스킬이 경력에서만 요구되는 성장 스킬인가. (JD 본문이 없어 "필수/우대"를 직접
   파싱할 수 없으므로, 경력 구간을 대체 축으로 사용한다.)
3. **역량 갭 진단** — 사용자가 보유 스킬을 입력하면, 시장 요구 대비 부족한 스킬을
   언급률 · 신입 가중치 · 최신성으로 가중해 학습 우선순위로 정렬한다.

### 직무 범위

데이터 분석가 / 데이터 엔지니어 / 데이터 사이언티스트 / BI / 그로스.
수집은 키워드 리스트로, 분류는 `job-code` + `keyword` 태그 조합 규칙으로 한다.

### 명시적으로 스코프 아웃

- 스타트업 전용 분석 — 사람인 커버리지 한계로 "채용시장 전반"으로 프레이밍하고,
  기업형태 필터 서브셋만 부가 분석으로 제공.
- 연봉 예측/추천 모델 — 연봉 필드 결측이 많아 스킬 분석에 집중.
- 원티드·랠릿·점프잇 등 타 채용 보드 — stretch goal.
- 로그인 / 개인 계정 / 저장된 대시보드 / 알림 — 갭 진단은 세션 단위 입력.
- 공고 개별 리스트·검색 — 사람인이 이미 하는 일.

## 데이터 소스

**사람인 오픈 API — Job Search API** (`https://oapi.saramin.co.kr/job-search`)

- 인증: `access-key` (이용신청 → 승인 → 앱 등록 후 발급). 2026-09-04 현재 승인 대기.
- 일일 호출 제한: **500회/일**.
- 응답 형식: JSON (`Accept: application/json`).

### API가 주는 필드 (확인 완료)

| 필드 | 내용 |
|---|---|
| `id`, `url` | 공고 번호, 표준 URL |
| `active` | 진행(1) / 마감(0) |
| `posting-timestamp` / `posting-date` | 게시일 |
| `modification-timestamp` | 수정일 |
| `expiration-timestamp` / `expiration-date` | 마감일 |
| `close-type` | 1 접수마감일 / 2 채용시 / 3 상시 / 4 수시 |
| `company/name` (+ `@href`) | 기업명, 기업정보 페이지 |
| `position/title` | 공고 제목 |
| `position/location` (`@code`) | 지역 코드 + 지역명 |
| `position/job-type` (`@code`) | 근무형태 |
| `position/industry` (`@code`) | 업종 |
| `position/job-mid-code` (`@code`) | 상위 직무코드 |
| `position/job-code` (`@code`, 다중) | 직무코드 + 직무명 |
| `position/experience-level` (`@code`, `@min`, `@max`) | 경력 (신입=1 / 경력=2 / 신입·경력=3 / 무관=0, 연차 min~max) |
| `position/required-education-level` (`@code`) | 학력 |
| `keyword` | **쉼표 구분 태그 문자열** |
| `salary` (`@code`) | 연봉 구간 |
| `read-cnt` / `apply-cnt` | 조회수 / 지원자수 (`fields=count` 요청 시) |
| `industry-keyword-code` / `job-code-keyword-code` | 상세분류 코드 (`fields=keyword-code` 요청 시) |

### API가 주지 않는 것

- **JD 본문(직무내용) 텍스트** — 따라서 자격요건 / 우대사항 섹션 구분 불가.

### `keyword` 태그 필드 실측 (2026-09-04, 사람인 공개 상세페이지)

- [어니컴] 데이터 분석 서비스 개발자:
  `IT개발·데이터, 빅데이터, AI(인공지능), 텍스트마이닝, 데이터마이닝, 데이터분석가,
  Java, Spring, 앱개발, 백엔드/서버개발, jupyterlab, Python, 데이터시각화, 딥러닝,
  Linux, WAS, Docker, 기획·전략, 데이터분석, 서울, 용산구`
- [세르딕] 풀스택 개발자:
  `Apache, AWS, Docker, Git, Javascript, Linux, Node.js, MySQL, OpenCV, Python,
  Ubuntu, Redis, SaaS, 클라우드, Kubernetes, TypeScript, PostgreSQL, ReactJS,
  HTML5, CSS3, C++, AI(인공지능), 서울, 강남구`

관찰:
- 실제 기술스택 태그가 풍부하다 → keyword 태그 기반 스킬 추출은 유효하다.
- 노이즈가 섞인다: 직무 카테고리(`IT개발·데이터`, `백엔드/서버개발`), 도메인
  (`빅데이터`, `텍스트마이닝`), **지역(`서울`, `용산구`)** → 화이트리스트 사전으로
  필터링한다.
- 표기 변형 정규화 필요: `jupyterlab`, `ReactJS`, `Node.js`, `HTML5` 등.
- 제목이 오해를 부른다: "데이터 분석 서비스 개발자"는 실제로 Java/Spring 백엔드
  → job_group 분류는 제목이 아니라 태그·직무코드 조합으로 한다.
- 미확인: API가 이 태그를 전부 주는지 일부만 주는지 → 승인 후 스파이크에서 확인.

## 아키텍처

### 파이프라인 (4단계, 각 단계 독립 실행·테스트 가능)

```
[사람인 Job Search API]
      │  매일 1회 (GitHub Actions cron, KST 06:00)
      ▼
  collector      키워드별 검색 → 원본 JSON 그대로 raw_postings 에 upsert (멱등)
      ▼
  normalizer     raw_postings → postings 정제
                 (job_group 매핑, 게시/마감일 파싱, 지역·경력·학력·업종 표준화,
                  중복 공고 판정 → dedup_group_id)
      ▼
  skill_extractor  keyword 태그 + title → 토큰화 → 사전 매칭(화이트리스트)
                   → posting_skills 적재. 미매칭 토큰은 unmatched_terms 누적
      ▼
  aggregator     일 단위 스냅샷 집계 → skill_daily_stats
                 (job_group × skill × 날짜 → 활성 공고 중 언급 수 / 총수 / 비율)
      ▼
  [Postgres]  ◄── FastAPI (읽기 전용 API)
      ▼
  [Next.js 대시보드]
```

**설계 원칙**

- **단계 분리**: 각 단계는 앞 단계가 쓴 DB 테이블만 읽는다. 함수 직접 호출로
  엮지 않는다. 데이터 소스가 추가돼도 collector만 바뀐다.
- **원본 불변**: `raw_postings.raw_json`은 API 응답을 그대로 보존. 정제 로직 버그
  시 재처리 가능.
- **멱등성**: 모든 단계가 재실행 안전 (upsert). cron이 중복 실행돼도 결과 동일.
- **결정적 코어**: LLM은 파이프라인 밖. 사전 확장 후보만 제안하고, 실제 반영은
  사람이 `skill_aliases.yaml`에 커밋 → 파이프라인은 순수 규칙 기반.

### 배포 토폴로지

| 구성요소 | 호스팅 | 비용 |
|---|---|---|
| 파이프라인 실행 | GitHub Actions cron | 무료 |
| Postgres | Supabase 무료 티어 (500MB) | 무료 |
| FastAPI (읽기 전용) | Render 또는 Railway | $0~7/월 |
| Next.js 대시보드 | Vercel | 무료 |
| LLM 사전 발굴 배치 | 주 1회 Actions + Claude API | < 1,000원/월 |

- Actions Secrets: `SARAMIN_API_KEY`, `DATABASE_URL`, (배치용) `ANTHROPIC_API_KEY`.
- 백업: Supabase 자동 백업 + 주간 `pg_dump`를 Actions artifact로 보관.

## 데이터 모델

```
raw_postings
  posting_id     TEXT PK          -- 사람인 공고 id
  keyword_query  TEXT             -- 수집에 쓰인 검색 키워드
  raw_json       JSONB            -- API 응답 원본
  first_seen_at  TIMESTAMPTZ
  last_seen_at   TIMESTAMPTZ      -- 마지막으로 검색결과에 나온 시각
  is_active      BOOLEAN          -- 최근 수집에서 사라지면 false (마감 추정)

postings                          -- 정제된 공고 (raw 와 1:1)
  posting_id       TEXT PK FK
  company_name     TEXT
  company_href     TEXT NULL
  title            TEXT
  keyword_raw      TEXT           -- raw_json 의 keyword 필드 원본 (스킬 추출 입력)
  job_group        TEXT           -- 'DA'|'DE'|'DS'|'BI'|'GROWTH'|'ETC'
  job_code_names   TEXT[]         -- 직무명 배열
  industry_code    TEXT NULL
  industry_name    TEXT NULL
  company_type     TEXT NULL      -- 대기업/중견/중소/스타트업(추정)
  experience_code  TEXT NULL      -- 0 무관 / 1 신입 / 2 경력 / 3 신입·경력
  experience_min   INT NULL       -- 연차 하한
  experience_max   INT NULL
  education_code   TEXT NULL
  location_code    TEXT NULL
  location_sido    TEXT NULL
  salary_code      TEXT NULL
  posted_date      DATE
  expiration_date  DATE NULL
  close_type       TEXT NULL
  read_cnt         INT NULL
  apply_cnt        INT NULL
  dedup_group_id   TEXT           -- 동일 공고 재게시 묶음

skills
  skill_id      TEXT PK           -- 'sql', 'python', 'tableau', 'airflow'
  display_name  TEXT
  category      TEXT              -- language|db|bi_viz|orchestration|cloud|ml|stats|infra|soft

skill_aliases                     -- git 버전 관리, skill_aliases.yaml 에서 로드
  alias      TEXT PK              -- '에스큐엘', 'ms sql', 'sequel'
  skill_id   TEXT FK

posting_skills                    -- 공고 × 스킬 (추출 결과)
  posting_id    TEXT FK
  skill_id      TEXT FK
  matched_from  TEXT              -- 'tag' | 'title'
  matched_alias TEXT
  PRIMARY KEY (posting_id, skill_id)

skill_daily_stats                 -- 대시보드가 읽는 집계 테이블
  snapshot_date DATE
  job_group     TEXT
  skill_id      TEXT
  posting_count INT               -- 해당일 활성 공고 중 이 스킬 언급 수 (dedup 그룹당 1)
  active_total  INT               -- 해당일 해당 job_group 활성 공고 총수 (dedup 적용)
  ratio         NUMERIC
  PRIMARY KEY (snapshot_date, job_group, skill_id)

skill_daily_stats_by_experience   -- 신입/경력 분리 집계
  snapshot_date   DATE
  job_group       TEXT
  skill_id        TEXT
  experience_band TEXT            -- 'junior' | 'senior'
  posting_count   INT
  active_total    INT
  ratio           NUMERIC
  PRIMARY KEY (snapshot_date, job_group, skill_id, experience_band)

unmatched_terms
  term            TEXT PK
  frequency       INT
  example_posting TEXT
  first_seen_at   TIMESTAMPTZ

llm_alias_suggestions
  candidate_term  TEXT PK
  suggested_skill TEXT NULL
  example_posting TEXT
  frequency       INT
  status          TEXT            -- 'pending' | 'accepted' | 'rejected'
  reviewed_at     TIMESTAMPTZ NULL

pipeline_runs                     -- 데이터 품질 모니터링
  run_id            TEXT PK
  started_at        TIMESTAMPTZ
  finished_at       TIMESTAMPTZ NULL
  status            TEXT           -- 'ok' | 'failed'
  postings_collected INT
  postings_new       INT
  unmatched_ratio    NUMERIC
  ungrouped_ratio    NUMERIC       -- job_group = ETC 비율
  notes              TEXT NULL
```

### 중복 공고 처리 (`dedup_group_id`)

같은 회사가 같은 포지션을 재게시하거나, 한 공고가 여러 검색 키워드에 잡힌다.

- 판정 키: `회사명 + 정규화된 제목 + experience_code` 가 같고 게시일 간격 90일 이내
  → 같은 그룹.
- 제목 정규화: 대괄호 태그 제거, 공백/특수문자 정리, 경력 표기 제거.
- **모든 집계는 dedup 그룹당 1건으로 카운트**한다 (재게시가 통계를 왜곡하지 않도록).

### job_group 분류 규칙

우선순위 순으로 적용, 첫 매치 채택:

1. `job-code` 명에 강한 신호가 있으면 그것 (`데이터 사이언티스트` → DS,
   `데이터엔지니어` → DE, `BI` → BI).
2. keyword 태그 집합으로 판정 (스킬 프로파일 기반: 오케스트레이션·파이프라인 태그
   비중이 높으면 DE, 시각화·리포팅 위주면 BI, 통계·ML 위주면 DS).
3. 제목 키워드는 보조 신호로만.
4. 어디에도 확실히 안 맞으면 `ETC` 로 격리 (집계에서 제외하되 수집·보관은 함).

`ungrouped_ratio`(ETC 비율)를 pipeline_runs 에 기록해 분류 규칙 품질을 추적한다.

## 스킬 추출 파이프라인 상세

입력: `postings.keyword_raw`(원본 태그 문자열, raw_json 에서), `postings.title`.

1. **토큰화** — 쉼표 분리 → trim → 영문 소문자화 → 전각·반각 정규화 →
   흔한 접미사 제거(`.js` 는 보존, 공백류 정리).
2. **태그 사전 매칭** — 각 토큰을 `skill_aliases` 에 정확 매치. 매치 시
   `posting_skills(..., matched_from='tag')`.
3. **제목 스캔** — title 에서 alias substring 매칭. 1~2글자 alias(`r`, `c`,
   `bi`)는 화이트리스트 + 단어경계 규칙으로만 허용. `matched_from='title'`.
4. **미매칭 토큰 수집** — 사전에 없는 토큰을 `unmatched_terms` 에 빈도 누적.
5. **LLM 사전 발굴 배치 (주 1회, 파이프라인 밖)** — `unmatched_terms` 상위 빈도
   50개를 LLM(Claude API 또는 로컬)에 보내 "데이터 직군 기술스킬인가? 표준 스킬명은?"
   판정 → `llm_alias_suggestions(status='pending')` → 사람이 리뷰 → 채택분을
   `skill_aliases.yaml` 에 커밋 → 다음 실행부터 규칙으로 반영.

핵심: 사전은 **데이터 직군 관련 스킬만** 등재한다. 사전에 없는 태그는 무시된다
(정밀도 우선, 재현율은 사전 관리로 점진 개선). `is_required` 컬럼은 없다.

`skill_aliases.yaml` 형식:

```yaml
- skill_id: sql
  display_name: SQL
  category: language
  aliases: [sql, 에스큐엘, "ms sql", mssql, sequel, tsql, plsql]
- skill_id: airflow
  display_name: Apache Airflow
  category: orchestration
  aliases: [airflow, "apache airflow", 에어플로우]
```

## 분석 레이어 (FastAPI 읽기 전용)

### 5-1. 트렌드

- 입력: `job_group`, `skill_id[]`, 기간.
- 출력: 날짜별 언급률(`ratio`) 시계열, 7일 이동평균 옵션.
- "신규 등장" 감지: 특정 스킬이 처음으로 언급률 임계값(예: 3%)을 넘긴 스냅샷 표시.
- 한계: 시계열은 관측 데이터가 쌓여야 의미가 생긴다. 초기에는 현재 스냅샷 중심이며,
  대시보드에 "관측 시작일"을 표시한다.

### 5-2. 신입 vs 경력 스킬 갭

- `skill_daily_stats_by_experience` 사용. junior = `experience_code in (0,1,3)`,
  senior = `experience_code in (2)` (경계는 구현 시 확정, min 연차도 고려).
- 스킬별 두 밴드의 언급률 차이(senior_ratio - junior_ratio)를 정렬.
- 해석 레이블: junior 언급률이 높으면 "진입장벽", senior 에서만 높으면 "성장 스킬".

### 5-3. 역량 갭 진단

- 입력: 사용자가 체크한 보유 스킬 집합 (프론트, 로그인 없음), 대상 job_group,
  대상 경력 밴드 (기본: DA, junior).
- 미보유 스킬 각각에 점수:
  `score = ratio × junior_weight × recency_weight`
  - `junior_weight = junior_ratio / overall_ratio` (신입 공고에서 더 요구될수록 가중)
  - `recency_weight = 최근 30일 ratio / 전체 기간 ratio` (뜨는 스킬 가중)
- 출력: 학습 우선순위 정렬 리스트 + "이 스킬을 배우면 대상 공고 커버리지 +X%p"
  (커버리지 = 사용자 스킬셋으로 "요구 스킬 모두 충족"되는 공고 비율).
- 순수 계산. 개인정보 저장 안 함.

### 5-4. 부가 축 (여유 시)

- 산업별 스킬 프로파일 (히트맵).
- 경쟁률(`apply_cnt / read_cnt`) × 스킬 조합.
- 연봉 구간 × 스킬 (표본 부족하면 생략).

## 프론트엔드 (Next.js App Router)

단일 대시보드 + 4개 뷰:

1. **개요** — 활성 공고 수, job_group 분포, 최다 요구 스킬 Top 15, 마지막 수집 시각.
2. **트렌드** — 스킬 멀티선택 → 언급률 시계열 라인차트, 이동평균 토글, 신규 등장 마커,
   "관측 N일치" 배너.
3. **신입 vs 경력** — 스킬별 두 밴드 발산형 막대, 차이 순 정렬, "진입장벽 / 성장 스킬"
   요약.
4. **역량 갭 진단** — 스킬 체크박스 그리드 → 대상 직무·경력 선택 → 학습 우선순위
   카드 리스트 (점수, 언급률, 커버리지 증분).

기술: 서버 컴포넌트로 FastAPI 호출, Recharts, 선택 상태는 URL 쿼리스트링(로컬스토리지
백업), 다크모드·모바일 반응형.

## 테스트 & 데이터 품질

- **단위 테스트 (pytest)**: 로더(스키마 검증), 정규화(코드 매핑, 경력 파싱, dedup
  판정, job_group 분류), 스킬 추출(사전 매칭, 화이트리스트 필터, 제목 스캔 경계),
  집계(비율, 신입/경력 분리), 갭 점수 계산.
- **픽스처**: 손으로 만든 현실적인 API 응답 샘플(2026-09-04 실측 태그 패턴 반영).
  승인 전에도 이걸로 개발.
- **데이터 품질 모니터링**: 실행마다 `pipeline_runs` 기록 — 수집 수, 신규 수,
  미매칭 토큰 비율, ETC 비율, 전일 대비 증감. 임계값 위반 시 Actions 실패.
- **재현성**: `skill_aliases.yaml` git 버전 관리로 특정 시점 집계 재현 가능.
- **FastAPI**: 엔드포인트별 통합 테스트 (테스트 DB 시드 → 응답 스냅샷).

## 리스크 & 오픈 이슈

| 리스크 | 대응 |
|---|---|
| 사람인 API 승인 지연 (2026-09-04 대기 중) | 픽스처로 개발 병행, 승인 후 스파이크 1건으로 검증 |
| API 가 keyword 태그를 일부만 줄 수 있음 | 승인 후 스파이크에서 확인, 부족하면 title 스캔 비중 확대 |
| 스타트업 커버리지 약함 | "채용시장 전반"으로 프레이밍, company_type 필터 서브셋 부가 |
| 시계열 축적에 시간 필요 | 초기엔 스냅샷 중심, "관측 시작일" 명시 |
| job_group 오분류 (제목만 데이터인 개발 공고) | 태그+직무코드 규칙, 미분류는 ETC 격리, ungrouped_ratio 추적 |
| 일 500 콜 제한 | 키워드 리스트 최적화, 초기 백필 분할 |
| company_type 추정 부정확 | 부가 분석에만 사용, 본 분석은 전체 대상 |

## 구현 단계 계획

### Phase A — API 없이 진행 (승인 대기 중 병행)

1. 프로젝트 스캐폴딩: 폴더 구조, `pyproject.toml`/`requirements.txt`, `.gitignore`,
   `.env.example`, git init, GitHub repo 생성.
2. DB 스키마 + 마이그레이션 (로컬 Docker Postgres 또는 Supabase).
3. 사람인 코드표 확보 (지역/산업/직무/경력/학력) — 공개 문서에서 다운로드,
   `job-code → job_group` 매핑 테이블 작성.
4. `skill_aliases.yaml` 초안 큐레이션 — 데이터 직군 스킬 사전 (GA4 프로젝트의
   채용공고 요구사항 분석 결과 + 2026-09-04 실측 태그 참고).
5. API 응답 픽스처 작성 (데이터 직군 공고 여러 유형).
6. normalizer / skill_extractor / aggregator 구현 + 단위 테스트 (픽스처 대상).
7. FastAPI 엔드포인트 + 통합 테스트 (시드 DB).
8. Next.js 대시보드 (목 데이터 → 픽스처 API).
9. GitHub Actions cron 워크플로 스켈레톤 (더미 키).

### Phase B — API 승인 후

10. 스파이크: 실제 호출 1건으로 keyword 태그 완전성·필드 확인. 필요시 설계 조정.
11. collector 구현 + 실데이터 수집 시작 (백필 분할).
12. 실데이터로 job_group 분류·스킬 추출 품질 검증, 사전·규칙 튜닝.
13. LLM 사전 발굴 배치 워크플로.
14. 프로덕션 배포 (Supabase / Render / Vercel), cron 활성화.
15. 관측 데이터 축적 → 트렌드 뷰 실데이터 전환.
16. 두괄식 케이스 스터디 문서 + Notion source of truth 페이지.

### 코어 완성 기준 (지원 시 보여줄 수 있는 최소선)

- 라이브 URL 에서 개요 + 신입/경력 갭 + 역량 갭 진단이 실데이터로 동작.
- GitHub Actions 로 매일 자동 수집이 돌고 있음 (로그로 증명).
- README + 두괄식 1페이지 (결론 → 방법 → 한계).
- 트렌드 뷰는 "관측 시작" 상태로 공개, 데이터가 쌓이며 성장.

## 참고

- 병행 원칙: 지원은 2026-09-15에 시작한다. 이 프로젝트는 지원과 병행하며,
  지원 시작을 미루는 사유가 되지 않는다.
- Notion source of truth 페이지는 Phase B 진입 시 생성한다.
