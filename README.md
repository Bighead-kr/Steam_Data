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

## 스키마 변경 규칙

- `src/tracker/schema.py`에서 SQLAlchemy ORM 정의 변경 후, 반드시 Alembic 마이그레이션도 함께 생성하세요.
- `alembic revision --autogenerate -m "설명"` 후 검수 및 실행.

## 스펙 문서

[스팀 저평가 게임 발굴 웹앱 — 설계 문서](docs/superpowers/specs/2026-09-05-steam-hidden-gems-design.md)
