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
`max_price_cents`, `limit` 쿼리 파라미터로 필터링할 수 있다.

## 파이프라인 실행

```bash
python scripts/run_pipeline.py
```

Steam/SteamSpy 수집(`collect_games`, Phase B에서 구현 예정) →
정규화(`run_normalizer`) → 점수 계산(`run_scorer`) → `pipeline_runs`에 실행
기록 저장까지 한 번에 수행한다. `.github/workflows/pipeline.yml`이 이
스크립트를 주기적으로(또는 수동으로) 실행한다.

## 웹앱 (`web/`)

```bash
cd web
npm install
npm run dev
```

Next.js로 만든 검색 UI로, `NEXT_PUBLIC_API_BASE_URL`(기본값
`http://localhost:8000`)로 FastAPI 서버에 요청해 결과를 렌더링한다.

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
