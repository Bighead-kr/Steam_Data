# 한국 데이터 직군 채용시장 트래커

사람인 오픈 API로 한국 데이터 직군 채용 공고를 매일 수집해, 요구 역량의 시계열 변화 · 신입/경력 스킬 갭 · 개인 역량 갭을 보여주는 라이브 웹 서비스.

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

[한국 데이터 직군 채용시장 트래커 — 설계 문서](docs/superpowers/specs/2026-09-04-data-job-market-tracker-design.md)
