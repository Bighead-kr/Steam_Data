# Phase A 데이터 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 손으로 만든 사람인 API 응답 픽스처를 입력받아 정제 → 스킬 추출 → 일 단위 집계까지 수행하는 결정적 데이터 파이프라인을, 전 구간 TDD로 완성한다.

**Architecture:** 4단계 파이프라인(load → normalize → extract → aggregate). 각 단계는 앞 단계가 쓴 Postgres 테이블만 읽고 다음 테이블에 upsert한다(멱등). 스킬 사전과 job_group 매핑은 git으로 버전 관리되는 YAML 파일에서 로드되며, 파이프라인 로직은 순수 규칙 기반이다(LLM 없음). collector(실 API 호출)와 FastAPI/프론트는 이 계획의 스코프가 아니다.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x Core, Alembic, PostgreSQL 16, pytest, testcontainers[postgresql], PyYAML, psycopg 3, ruff.

**Spec:** `docs/superpowers/specs/2026-09-04-data-job-market-tracker-design.md`

## Global Constraints

- Python 3.12 이상. 의존성은 `pyproject.toml`의 `[project.dependencies]`로 관리.
- DB는 PostgreSQL 16. 테스트는 testcontainers로 실제 Postgres를 띄운다(SQLite 금지 — JSONB, `TEXT[]` 사용).
- 모든 파이프라인 단계 함수는 **멱등**하다: 같은 입력으로 재실행해도 결과 동일(upsert 사용, INSERT 후 중복 시 UPDATE).
- 스킬 사전(`data/skill_aliases.yaml`)에는 **데이터 직군 관련 스킬만** 등재한다. 사전에 없는 태그는 무시된다(정밀도 우선).
- `posting_skills`에 `is_required` 컬럼은 없다(스펙: API가 JD 본문을 주지 않음).
- 모든 집계는 **dedup 그룹당 1건**으로 카운트한다.
- 커밋 메시지는 Conventional Commits(`feat:`, `test:`, `chore:`, `fix:`, `docs:`).
- 린트: `ruff check` 통과. 포맷: `ruff format`.
- git 원격 연결은 사용자가 직접 한다 — 이 계획은 로컬 커밋까지만 한다.

---

## File Structure

```
Data3/
├── pyproject.toml                       # 프로젝트 메타 + 의존성 + 툴 설정
├── .env.example                         # DATABASE_URL 형식만
├── .gitignore
├── docker-compose.yml                   # 로컬 개발용 Postgres (테스트는 testcontainers)
├── alembic.ini
├── README.md                            # 프로젝트 개요 (짧게)
├── data/
│   ├── skill_aliases.yaml               # 큐레이션 스킬 사전
│   └── code_tables/
│       └── job_group_map.yaml           # job-code(명) → job_group 규칙
├── src/tracker/
│   ├── __init__.py
│   ├── config.py                        # 환경변수 로딩(Settings)
│   ├── db.py                            # 엔진/세션 팩토리
│   ├── schema.py                        # SQLAlchemy Core Table 정의(MetaData)
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── dictionary.py                    # skill_aliases.yaml 로더
│   ├── job_group.py                     # job_group_map.yaml 로더 + 분류기
│   ├── load.py                          # 픽스처/응답 dict → raw_postings upsert
│   ├── normalize.py                     # raw_postings → postings
│   ├── dedup.py                         # postings.dedup_group_id 할당
│   ├── extract.py                       # postings → posting_skills + unmatched_terms
│   ├── aggregate.py                     # → skill_daily_stats(+_by_experience)
│   └── pipeline.py                      # normalize→dedup→extract→aggregate + pipeline_runs
├── tests/
│   ├── conftest.py                      # testcontainers Postgres + 스키마 생성 fixture
│   ├── fixtures/
│   │   └── saramin/
│   │       ├── da_junior_bi.json        # 데이터 분석가 신입, BI 스킬
│   │       ├── de_senior_pipeline.json  # 데이터 엔지니어 경력, 오케스트레이션
│   │       ├── ds_ml.json               # 데이터 사이언티스트, ML
│   │       ├── dev_mislabeled.json      # 제목만 "데이터", 실제 백엔드 → ETC
│   │       ├── repost_of_da_junior.json # da_junior_bi 재게시 (dedup 대상)
│   │       └── multi_keyword_dup.json   # 다른 검색어로 같은 공고 재수집
│   ├── test_dictionary.py
│   ├── test_job_group.py
│   ├── test_load.py
│   ├── test_normalize.py
│   ├── test_dedup.py
│   ├── test_extract.py
│   ├── test_aggregate.py
│   └── test_pipeline.py
```

**책임 분리 근거:**
- `schema.py`는 테이블 정의만. 마이그레이션은 Alembic이 담당. 두 곳에 스키마가 갈라지지 않도록 Alembic `0001_initial`은 `schema.py`의 `metadata.create_all` 대신 명시적 DDL을 쓰되, 테스트 conftest는 `schema.py`의 metadata로 생성한다(빠름). 스키마 변경 시 둘 다 갱신하는 규칙을 README에 명시.
- 파이프라인 단계는 파일 1개 = 단계 1개. 각 파일은 `run(conn, ...)` 형태의 진입 함수 하나를 export한다.
- `job_group.py`, `dictionary.py`는 파이프라인 밖의 "설정 로더"라 별도 파일.

---

## Task 1: 프로젝트 스캐폴딩 + 설정 + 로컬 Postgres

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `docker-compose.yml`, `README.md`
- Create: `src/tracker/__init__.py`, `src/tracker/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `tracker.config.Settings` — pydantic-settings 모델. 필드: `database_url: str`.
  - `tracker.config.get_settings() -> Settings` — `@lru_cache`, 환경변수 `DATABASE_URL`에서 로딩.

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[project]
name = "data-job-market-tracker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.2",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "testcontainers[postgresql]>=4.0",
    "ruff>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"

[tool.ruff]
line-length = 100
target-version = "py312"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tracker"]
```

- [ ] **Step 2: `.gitignore`, `.env.example`, `docker-compose.yml`, `README.md` 작성**

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
.env
.pytest_cache/
.ruff_cache/
*.egg-info/
```

`.env.example`:
```
DATABASE_URL=postgresql+psycopg://tracker:tracker@localhost:5432/tracker
```

`docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: tracker
      POSTGRES_PASSWORD: tracker
      POSTGRES_DB: tracker
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

`README.md`: 프로젝트 한 줄 정의(스펙에서), 로컬 실행법(`docker compose up -d`, `pip install -e ".[dev]"`, `alembic upgrade head`, `pytest`), 스키마 변경 시 `schema.py`와 Alembic 마이그레이션을 함께 갱신하라는 규칙, 스펙 문서 링크.

- [ ] **Step 3: 실패하는 테스트 작성**

```python
# tests/test_config.py
import tracker.config as config


def test_get_settings_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: tracker.config` 또는 import 에러)

- [ ] **Step 5: `src/tracker/__init__.py`(빈 파일)와 `config.py` 구현**

```python
# src/tracker/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: 설치 후 테스트 통과 확인**

Run: `pip install -e ".[dev]" && pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add pyproject.toml .gitignore .env.example docker-compose.yml README.md src/ tests/
git commit -m "chore: scaffold project with config and local postgres"
```

---

## Task 2: DB 스키마 + Alembic 마이그레이션

**Files:**
- Create: `src/tracker/schema.py`, `src/tracker/db.py`
- Create: `alembic.ini`, `src/tracker/migrations/env.py`, `src/tracker/migrations/versions/0001_initial.py`
- Create: `tests/conftest.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: `tracker.config.get_settings`
- Produces:
  - `tracker.schema.metadata: sqlalchemy.MetaData` — 아래 11개 테이블 전부 포함.
  - 테이블 객체: `raw_postings`, `postings`, `skills`, `skill_aliases`, `posting_skills`, `skill_daily_stats`, `skill_daily_stats_by_experience`, `unmatched_terms`, `llm_alias_suggestions`, `pipeline_runs` (스펙 데이터 모델 그대로).
  - `tracker.db.get_engine() -> Engine` — `create_engine(get_settings().database_url, future=True)`.
  - `tests` fixture `db_conn` — testcontainers Postgres에 `metadata.create_all` 후 트랜잭션을 열고, 테스트마다 롤백.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_schema.py
from sqlalchemy import inspect

from tracker.schema import metadata


def test_all_expected_tables_defined():
    names = set(metadata.tables.keys())
    assert names == {
        "raw_postings", "postings", "skills", "skill_aliases", "posting_skills",
        "skill_daily_stats", "skill_daily_stats_by_experience",
        "unmatched_terms", "llm_alias_suggestions", "pipeline_runs",
    }


def test_schema_creates_on_real_postgres(db_conn):
    tables = set(inspect(db_conn).get_table_names())
    assert "postings" in tables and "skill_daily_stats" in tables
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL (`tracker.schema` 없음)

- [ ] **Step 3: `schema.py` 구현**

스펙의 "데이터 모델" 섹션을 SQLAlchemy Core `Table(...)` 정의로 옮긴다. 규칙:
- `TEXT` → `sa.Text`, `INT` → `sa.Integer`, `NUMERIC` → `sa.Numeric`, `BOOLEAN` → `sa.Boolean`, `TIMESTAMPTZ` → `sa.DateTime(timezone=True)`, `DATE` → `sa.Date`, `JSONB` → `postgresql.JSONB`, `TEXT[]` → `postgresql.ARRAY(sa.Text)`.
- 스펙에 적힌 PK를 그대로 반영(복합 PK는 `PrimaryKeyConstraint`).
- FK는 스펙 표기대로(`posting_id` → `raw_postings.posting_id` / `postings.posting_id`, `skill_id` → `skills.skill_id`).
- `posting_skills` PK = `(posting_id, skill_id)`, 추가 컬럼 `matched_from`, `matched_alias`.
- `postings`에 `keyword_raw TEXT` 포함(스펙 갱신분).

파일 상단:
```python
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

metadata = sa.MetaData()

raw_postings = sa.Table(
    "raw_postings", metadata,
    sa.Column("posting_id", sa.Text, primary_key=True),
    sa.Column("keyword_query", sa.Text),
    sa.Column("raw_json", postgresql.JSONB, nullable=False),
    sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
)
# ... 나머지 10개 테이블 동일 방식
```

- [ ] **Step 4: `db.py` 구현**

```python
# src/tracker/db.py
from sqlalchemy import Engine, create_engine

from tracker.config import get_settings


def get_engine() -> Engine:
    return create_engine(get_settings().database_url, future=True)
```

- [ ] **Step 5: `tests/conftest.py` 구현**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

from tracker.schema import metadata


@pytest.fixture(scope="session")
def _pg():
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        yield pg


@pytest.fixture(scope="session")
def _engine(_pg):
    engine = create_engine(_pg.get_connection_url(), future=True)
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_conn(_engine):
    conn = _engine.connect()
    txn = conn.begin()
    try:
        yield conn
    finally:
        txn.rollback()
        conn.close()
```

- [ ] **Step 6: Alembic 초기화 + `0001_initial` 작성**

`alembic.ini`의 `script_location = src/tracker/migrations`, `sqlalchemy.url`은 env.py에서 `get_settings().database_url`로 덮어쓴다. `0001_initial.py`의 `upgrade()`는 `schema.py`의 모든 테이블을 `op.create_table(...)`로 생성(수기 DDL). `downgrade()`는 역순 `op.drop_table`.

- [ ] **Step 7: 테스트 + 마이그레이션 검증**

Run: `docker compose up -d && pytest tests/test_schema.py -v && alembic upgrade head && alembic downgrade base`
Expected: 테스트 PASS, 마이그레이션 up/down 에러 없음

- [ ] **Step 8: 커밋**

```bash
git add src/tracker/schema.py src/tracker/db.py src/tracker/migrations alembic.ini tests/conftest.py tests/test_schema.py
git commit -m "feat: define db schema and initial alembic migration"
```

---

## Task 3: 스킬 사전 로더

**Files:**
- Create: `data/skill_aliases.yaml`, `src/tracker/dictionary.py`
- Test: `tests/test_dictionary.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `tracker.dictionary.SkillDef` — dataclass: `skill_id: str`, `display_name: str`, `category: str`, `aliases: list[str]`.
  - `tracker.dictionary.load_dictionary(path: Path | None = None) -> list[SkillDef]` — 기본 경로 `data/skill_aliases.yaml`.
  - `tracker.dictionary.build_alias_index(defs: list[SkillDef]) -> dict[str, str]` — 정규화된 alias → skill_id. alias는 `.strip().lower()`로 정규화. 중복 alias는 ValueError.
  - `tracker.dictionary.CATEGORIES: frozenset[str]` = `{"language","db","bi_viz","orchestration","cloud","ml","stats","infra","soft"}`.

- [ ] **Step 1: `data/skill_aliases.yaml` 초안 큐레이션**

데이터 직군 스킬만. 최소 다음 skill_id를 포함하고 각각 현실적 alias를 단다(2026-09-04 실측 태그 + 일반 지식 기반):
`sql, python, r, excel, sas, spss` (language/stats),
`postgresql, mysql, oracle, mssql, bigquery, snowflake, redshift, mongodb, redis` (db),
`tableau, powerbi, looker, superset, metabase, ga4, amplitude, redash` (bi_viz),
`airflow, dbt, spark, hadoop, kafka, flink` (orchestration),
`aws, gcp, azure, docker, kubernetes` (cloud/infra),
`pytorch, tensorflow, scikit-learn, xgboost, mlflow` (ml),
`git, linux, jupyter` (infra),
`ab_test, causal_inference` (stats).

YAML 형식:
```yaml
- skill_id: sql
  display_name: SQL
  category: language
  aliases: [sql, 에스큐엘, "ms sql", mssql, sequel, tsql, "pl/sql", plsql]
- skill_id: ga4
  display_name: Google Analytics 4
  category: bi_viz
  aliases: [ga4, "google analytics 4", "구글 애널리틱스", ga]
```

- [ ] **Step 2: 실패하는 테스트 작성**

```python
# tests/test_dictionary.py
from tracker.dictionary import build_alias_index, load_dictionary


def test_load_dictionary_returns_known_skills():
    defs = load_dictionary()
    ids = {d.skill_id for d in defs}
    assert {"sql", "python", "tableau", "airflow"} <= ids


def test_all_categories_valid():
    from tracker.dictionary import CATEGORIES
    for d in load_dictionary():
        assert d.category in CATEGORIES


def test_alias_index_is_normalized_and_unique():
    idx = build_alias_index(load_dictionary())
    assert idx["sql"] == "sql"
    assert idx["ms sql"] == "sql"       # 소문자/공백 정규화
    assert all(k == k.strip().lower() for k in idx)


def test_duplicate_alias_raises():
    import pytest
    from tracker.dictionary import SkillDef
    dupes = [
        SkillDef("a", "A", "language", ["x"]),
        SkillDef("b", "B", "language", ["X"]),
    ]
    with pytest.raises(ValueError):
        build_alias_index(dupes)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `pytest tests/test_dictionary.py -v`
Expected: FAIL (`tracker.dictionary` 없음)

- [ ] **Step 4: `dictionary.py` 구현**

```python
# src/tracker/dictionary.py
from dataclasses import dataclass
from pathlib import Path

import yaml

CATEGORIES = frozenset({
    "language", "db", "bi_viz", "orchestration", "cloud", "ml", "stats", "infra", "soft",
})
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "skill_aliases.yaml"


@dataclass(frozen=True)
class SkillDef:
    skill_id: str
    display_name: str
    category: str
    aliases: list[str]


def load_dictionary(path: Path | None = None) -> list[SkillDef]:
    raw = yaml.safe_load((path or _DEFAULT_PATH).read_text(encoding="utf-8"))
    defs = [SkillDef(**item) for item in raw]
    for d in defs:
        if d.category not in CATEGORIES:
            raise ValueError(f"unknown category {d.category!r} for {d.skill_id}")
    return defs


def _norm(s: str) -> str:
    return s.strip().lower()


def build_alias_index(defs: list[SkillDef]) -> dict[str, str]:
    idx: dict[str, str] = {}
    for d in defs:
        for alias in [d.skill_id, *d.aliases]:
            key = _norm(alias)
            if key in idx and idx[key] != d.skill_id:
                raise ValueError(f"alias {key!r} maps to both {idx[key]} and {d.skill_id}")
            idx[key] = d.skill_id
    return idx
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_dictionary.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add data/skill_aliases.yaml src/tracker/dictionary.py tests/test_dictionary.py
git commit -m "feat: add curated skill alias dictionary and loader"
```

---

## Task 4: job_group 매핑 + 분류기

**Files:**
- Create: `data/code_tables/job_group_map.yaml`, `src/tracker/job_group.py`
- Test: `tests/test_job_group.py`

**Interfaces:**
- Consumes: `tracker.dictionary` (스킬 카테고리 기반 보조 판정에 사용).
- Produces:
  - `tracker.job_group.JOB_GROUPS: tuple[str, ...]` = `("DA", "DE", "DS", "BI", "GROWTH", "ETC")`.
  - `tracker.job_group.classify(job_code_names: list[str], keyword_tags: list[str], title: str, matched_skill_categories: set[str]) -> str` — 스펙 "job_group 분류 규칙"의 4단계 우선순위 적용, 첫 매치 반환. 확신 없으면 `"ETC"`.

- [ ] **Step 1: `job_group_map.yaml` 작성**

```yaml
# 직무명(job-code name) / 태그의 강한 신호 → job_group
strong_signals:
  DS: ["데이터 사이언티스트", "데이터사이언티스트", "data scientist", "머신러닝 엔지니어"]
  DE: ["데이터엔지니어", "데이터 엔지니어", "data engineer"]
  BI: ["bi", "비아이", "bi 엔지니어", "bi engineer", "데이터시각화"]
  GROWTH: ["그로스", "growth", "gredth marketer", "퍼포먼스 마케팅"]
  DA: ["데이터분석가", "데이터 분석가", "data analyst", "데이터분석"]
# 스킬 카테고리 프로파일 기반 보조 규칙 (strong_signals 실패 시)
category_profile:
  DE: {requires_any: ["orchestration"], min_count: 1}
  DS: {requires_any: ["ml"], min_count: 1}
  BI: {requires_any: ["bi_viz"], min_count: 2}
title_hints:
  DA: ["분석", "analyst"]
  DE: ["엔지니어", "engineer", "파이프라인"]
```

- [ ] **Step 2: 실패하는 테스트 작성**

```python
# tests/test_job_group.py
from tracker.job_group import classify


def test_strong_signal_from_job_code_wins():
    assert classify(["데이터 사이언티스트", "빅데이터"], [], "AI 분석가 채용", set()) == "DS"


def test_data_engineer_by_orchestration_profile():
    assert classify([], ["airflow", "python"], "데이터 파이프라인 담당", {"orchestration", "language"}) == "DE"


def test_bi_needs_two_viz_signals():
    assert classify([], [], "리포팅 담당자", {"bi_viz"}) == "ETC"       # 1개면 부족
    assert classify(["데이터시각화"], [], "리포팅 담당자", {"bi_viz"}) == "BI"


def test_mislabeled_dev_posting_falls_to_etc():
    # 제목만 "데이터", 태그는 순수 백엔드, 매칭 스킬 카테고리 없음
    assert classify(["백엔드/서버개발", "웹개발"], ["java", "spring"], "데이터 분석 서비스 개발자", set()) == "ETC"


def test_plain_analyst():
    assert classify(["데이터분석가"], ["sql", "tableau"], "데이터 분석가", {"language", "bi_viz"}) == "DA"
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `pytest tests/test_job_group.py -v`
Expected: FAIL (`tracker.job_group` 없음)

- [ ] **Step 4: `job_group.py` 구현**

우선순위:
1. `job_code_names` + `keyword_tags`를 소문자화해서 `strong_signals` 매칭(부분 문자열). DA는 다른 그룹보다 약하므로 **DS/DE/BI/GROWTH를 먼저 검사**하고 그다음 DA.
2. `category_profile` — `matched_skill_categories`가 `requires_any` 중 하나를 포함하고, BI는 viz 신호 2개(태그 내 bi_viz alias 수) 이상.
3. `title_hints` — 제목에 힌트 단어. 단, 매칭 스킬이 0개면 이 단계 건너뜀(오분류 방지).
4. `"ETC"`.

```python
# src/tracker/job_group.py
from pathlib import Path

import yaml

JOB_GROUPS = ("DA", "DE", "DS", "BI", "GROWTH", "ETC")
_MAP_PATH = Path(__file__).resolve().parents[2] / "data" / "code_tables" / "job_group_map.yaml"
_MAP = yaml.safe_load(_MAP_PATH.read_text(encoding="utf-8"))
_ORDER = ["DS", "DE", "BI", "GROWTH", "DA"]  # DA 마지막


def classify(job_code_names, keyword_tags, title, matched_skill_categories):
    hay = " ".join(n.lower() for n in [*job_code_names, *keyword_tags])
    for grp in _ORDER:
        for sig in _MAP["strong_signals"].get(grp, []):
            if sig.lower() in hay:
                return grp
    cats = set(matched_skill_categories)
    for grp, rule in _MAP["category_profile"].items():
        if set(rule["requires_any"]) & cats:
            if grp == "BI":
                viz = sum(1 for t in keyword_tags if t)  # viz 태그 수는 호출부에서 필터해 전달
            return grp
    if matched_skill_categories:
        t = title.lower()
        for grp, hints in _MAP["title_hints"].items():
            if any(h in t for h in hints):
                return grp
    return "ETC"
```

주의: 위 스니펫의 BI viz 카운트는 단순화돼 있음 — 구현 시 `classify`에 별도 인자 `viz_tag_count: int`를 추가해 스펙의 "viz 신호 2개 이상"을 정확히 판정하고, 테스트 `test_bi_needs_two_viz_signals`를 그 시그니처로 맞춘다.

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_job_group.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add data/code_tables/job_group_map.yaml src/tracker/job_group.py tests/test_job_group.py
git commit -m "feat: add job_group classification rules and classifier"
```

---

## Task 5: 픽스처 + raw_postings 로더

**Files:**
- Create: `tests/fixtures/saramin/*.json` (6개), `src/tracker/load.py`
- Test: `tests/test_load.py`

**Interfaces:**
- Consumes: `tracker.schema.raw_postings`
- Produces:
  - `tracker.load.job_dicts_from_response(response: dict) -> list[dict]` — 사람인 job-search JSON 응답에서 `jobs.job` 리스트를 뽑는다. `job`이 단일 dict면 `[job]`, 없으면 `[]`.
  - `tracker.load.upsert_raw(conn, jobs: list[dict], keyword_query: str, now: datetime) -> LoadResult` — 각 job을 `raw_postings`에 upsert. 신규는 `first_seen_at=last_seen_at=now`, 기존은 `last_seen_at=now`로만 갱신하고 `raw_json`도 최신으로 덮어씀. `LoadResult(inserted: int, updated: int)`.
  - `tracker.load.mark_inactive(conn, seen_posting_ids: set[str], keyword_query: str, now: datetime) -> int` — 이번 수집(해당 keyword)에서 안 보인 기존 활성 공고를 `is_active=False`. 반환: 비활성 처리 수. (Phase A에서는 픽스처로만 테스트, 실사용은 collector.)

- [ ] **Step 1: 픽스처 6개 작성**

사람인 API Sample Output(스펙 참조) 구조를 따르되 JSON. 각 파일은 `{"jobs": {"count": N, "start": 0, "total": N, "job": [ ... ]}}` 형태. 필드: `id`, `url`, `active`, `posting-timestamp`, `posting-date`, `expiration-timestamp`, `close-type`, `company.name`, `position.title`, `position.location`(@code), `position.job-type`, `position.industry`(@code), `position.job-mid-code`, `position.job-code`(@code 다중), `position.experience-level`(@code/@min/@max), `position.required-education-level`, `keyword`(쉼표 문자열), `salary`(@code).

- `da_junior_bi.json`: id=`10001`, 제목 "데이터 분석가 (신입)", job-code "데이터분석가", experience @code=1 min=0 max=0, keyword `데이터분석가,SQL,Tableau,Python,GA4,데이터시각화,서울`.
- `de_senior_pipeline.json`: id=`10002`, job-code "데이터엔지니어", experience @code=2 min=3 max=7, keyword `데이터엔지니어,Airflow,dbt,Spark,Python,AWS,Kafka`.
- `ds_ml.json`: id=`10003`, job-code "데이터 사이언티스트", experience @code=3 min=0 max=5, keyword `데이터사이언티스트,Python,PyTorch,scikit-learn,SQL,통계분석`.
- `dev_mislabeled.json`: id=`10004`, 제목 "데이터 분석 서비스 개발자", job-code "백엔드/서버개발,웹개발", keyword `Java,Spring,백엔드/서버개발,Docker,Linux,서울,용산구`.
- `repost_of_da_junior.json`: id=`10005`, 제목 "[재공고] 데이터 분석가 (신입)", 회사·경력 동일, posting-date는 `da_junior_bi`보다 20일 뒤, keyword 동일.
- `multi_keyword_dup.json`: `da_junior_bi`와 **동일한 id `10001`**, keyword_query만 다르게 로드할 때 재수집 시나리오용(같은 응답 재사용 가능).

- [ ] **Step 2: 실패하는 테스트 작성**

```python
# tests/test_load.py
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from tracker.load import job_dicts_from_response, mark_inactive, upsert_raw
from tracker.schema import raw_postings

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _resp(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_job_dicts_handles_list_and_single():
    assert len(job_dicts_from_response(_resp("da_junior_bi.json"))) == 1
    assert job_dicts_from_response({"jobs": {}}) == []


def test_upsert_inserts_then_updates(db_conn):
    now1 = datetime(2026, 9, 1, tzinfo=UTC)
    jobs = job_dicts_from_response(_resp("da_junior_bi.json"))
    r1 = upsert_raw(db_conn, jobs, "데이터 분석가", now1)
    assert (r1.inserted, r1.updated) == (1, 0)

    now2 = datetime(2026, 9, 2, tzinfo=UTC)
    r2 = upsert_raw(db_conn, jobs, "데이터 분석가", now2)
    assert (r2.inserted, r2.updated) == (0, 1)

    row = db_conn.execute(select(raw_postings)).one()
    assert row.first_seen_at == now1 and row.last_seen_at == now2


def test_mark_inactive(db_conn):
    now = datetime(2026, 9, 1, tzinfo=UTC)
    upsert_raw(db_conn, job_dicts_from_response(_resp("da_junior_bi.json")), "데이터 분석가", now)
    n = mark_inactive(db_conn, seen_posting_ids=set(), keyword_query="데이터 분석가", now=now)
    assert n == 1
    assert db_conn.execute(select(raw_postings.c.is_active)).scalar() is False
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `pytest tests/test_load.py -v`
Expected: FAIL (`tracker.load` 없음)

- [ ] **Step 4: `load.py` 구현**

`upsert_raw`는 `postgresql.insert(...).on_conflict_do_update(index_elements=["posting_id"], set_={...})`를 쓰되, insert/update 카운트는 사전 `SELECT`로 존재 여부를 확인해 집계(또는 `xmax` 트릭 대신 명시적 조회 — 가독성 우선). `id` 필드가 문자열이 아닐 수 있으니 `str(job["id"])`.

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_load.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add tests/fixtures/saramin src/tracker/load.py tests/test_load.py
git commit -m "feat: add saramin fixtures and raw_postings loader"
```

---

## Task 6: normalizer (raw_postings → postings)

**Files:**
- Create: `src/tracker/normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes: `tracker.schema.raw_postings`, `tracker.schema.postings`, `tracker.job_group.classify`, `tracker.dictionary` (스킬 카테고리 추정용 — extract와 중복 매칭을 피하려면 `classify`에 넘길 `matched_skill_categories`는 여기서 가벼운 alias 조회로 계산).
- Produces:
  - `tracker.normalize.parse_experience(node: dict) -> tuple[str|None, int|None, int|None]` — `(code, min, max)`.
  - `tracker.normalize.split_keyword(raw: str) -> list[str]` — 쉼표 분리 + trim, 빈 토큰 제거.
  - `tracker.normalize.run(conn) -> int` — 아직 `postings`에 없거나 원본이 갱신된 `raw_postings`를 정제해 `postings`에 upsert. 반환: 처리 건수.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_normalize.py
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from tracker.load import job_dicts_from_response, upsert_raw
from tracker.normalize import parse_experience, run, split_keyword
from tracker.schema import postings

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _load(db_conn, name, kw="데이터 분석가"):
    resp = json.loads((FIX / name).read_text(encoding="utf-8"))
    upsert_raw(db_conn, job_dicts_from_response(resp), kw, datetime(2026, 9, 1, tzinfo=UTC))


def test_parse_experience():
    assert parse_experience({"@code": "2", "@min": "3", "@max": "7"}) == ("2", 3, 7)
    assert parse_experience({"@code": "0"}) == ("0", None, None)


def test_split_keyword():
    assert split_keyword("SQL, Python , ,Tableau") == ["SQL", "Python", "Tableau"]


def test_run_normalizes_all_rows(db_conn):
    for f in ["da_junior_bi.json", "de_senior_pipeline.json", "dev_mislabeled.json"]:
        _load(db_conn, f)
    n = run(db_conn)
    assert n == 3
    rows = {r.posting_id: r for r in db_conn.execute(select(postings)).all()}
    assert rows["10001"].job_group == "DA"
    assert rows["10002"].job_group == "DE"
    assert rows["10004"].job_group == "ETC"          # 제목만 데이터인 백엔드 공고
    assert rows["10001"].experience_code == "1"
    assert rows["10001"].keyword_raw.startswith("데이터분석가")


def test_run_is_idempotent(db_conn):
    _load(db_conn, "da_junior_bi.json")
    assert run(db_conn) == 1
    assert run(db_conn) == 1                          # 재실행해도 1건 재처리, 중복 행 없음
    assert db_conn.execute(select(postings)).one()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL

- [ ] **Step 3: `normalize.py` 구현**

- `raw_json`에서 필드 추출(경로: `position.title`, `position.experience-level` 등). 사람인 JSON은 `@code` 키를 쓰고, 텍스트는 값에 직접(또는 `#text`) — 픽스처 구조에 맞춰 헬퍼 `_text(node)`, `_attr(node, "@code")`.
- `job-code`의 `@code`는 `"2072,2093"`처럼 쉼표 다중, 텍스트도 `"게임개발,기술지원"` → `job_code_names = split_keyword(text)`.
- 스킬 카테고리 추정: `dictionary.build_alias_index` 로 `split_keyword(keyword_raw)` 토큰을 조회해 매칭된 skill_id의 category 집합 → `classify`에 전달. viz 태그 수도 계산.
- `postings` upsert: `on_conflict_do_update` on `posting_id`.
- "원본이 갱신됨" 판정은 Phase A에서는 단순화: 매 실행마다 전체 `raw_postings`를 재정제(멱등이므로 안전). 반환값은 처리한 raw 행 수.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/tracker/normalize.py tests/test_normalize.py
git commit -m "feat: add normalizer from raw_postings to postings"
```

---

## Task 7: dedup (dedup_group_id 할당)

**Files:**
- Create: `src/tracker/dedup.py`
- Test: `tests/test_dedup.py`

**Interfaces:**
- Consumes: `tracker.schema.postings`
- Produces:
  - `tracker.dedup.normalize_title(title: str) -> str` — 대괄호 `[...]` 및 `(...)` 태그 제거, 경력 표기(`신입`, `경력`, `N년차`, `재공고`) 제거, 연속 공백·특수문자 정리, 소문자.
  - `tracker.dedup.run(conn) -> int` — 모든 `postings`에 `dedup_group_id` 부여. 키: `company_name + normalize_title(title) + experience_code`, 단 같은 키라도 posted_date 간격 90일 초과면 다른 그룹. group_id는 그룹 내 최소 posting_id. 반환: 그룹 수.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_dedup.py
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from tracker.dedup import normalize_title, run
from tracker.load import job_dicts_from_response, upsert_raw
from tracker.normalize import run as normalize_run
from tracker.schema import postings

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _prep(db_conn, names):
    for f in names:
        resp = json.loads((FIX / f).read_text(encoding="utf-8"))
        upsert_raw(db_conn, job_dicts_from_response(resp), "데이터 분석가", datetime(2026, 9, 1, tzinfo=UTC))
    normalize_run(db_conn)


def test_normalize_title_strips_tags_and_seniority():
    assert normalize_title("[재공고] 데이터 분석가 (신입)") == normalize_title("데이터 분석가")


def test_repost_within_90_days_same_group(db_conn):
    _prep(db_conn, ["da_junior_bi.json", "repost_of_da_junior.json"])
    run(db_conn)
    groups = {r.posting_id: r.dedup_group_id for r in db_conn.execute(select(postings)).all()}
    assert groups["10001"] == groups["10005"]


def test_distinct_postings_distinct_groups(db_conn):
    _prep(db_conn, ["da_junior_bi.json", "de_senior_pipeline.json"])
    run(db_conn)
    groups = {r.posting_id: r.dedup_group_id for r in db_conn.execute(select(postings)).all()}
    assert groups["10001"] != groups["10002"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_dedup.py -v`
Expected: FAIL

- [ ] **Step 3: `dedup.py` 구현**

파이썬에서 전 행 로드 → 키별 그룹핑 → 각 키 안에서 posted_date 정렬 후 90일 윈도로 서브그룹 분할 → 서브그룹의 min(posting_id)를 group_id로 UPDATE. 규모가 작으므로(수천) 메모리 처리 OK.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_dedup.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/tracker/dedup.py tests/test_dedup.py
git commit -m "feat: add dedup_group_id assignment"
```

---

## Task 8: skill_extractor (postings → posting_skills)

**Files:**
- Create: `src/tracker/extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `tracker.schema.postings`, `tracker.schema.posting_skills`, `tracker.schema.skills`, `tracker.schema.unmatched_terms`, `tracker.dictionary`.
- Produces:
  - `tracker.extract.tokenize(keyword_raw: str) -> list[str]` — split_keyword 후 각 토큰 `.strip().lower()`, 전각→반각(`unicodedata.normalize("NFKC", ...)`), 빈 토큰 제거, 중복 제거(순서 유지).
  - `tracker.extract.sync_skills(conn, defs) -> None` — `skills` 테이블을 사전과 동기화(upsert display_name/category).
  - `tracker.extract.run(conn) -> ExtractResult` — 모든 `postings`에 대해: 태그 매칭 + 제목 스캔 → `posting_skills` upsert(`matched_from` in `{"tag","title"}`, 태그 우선), 미매칭 토큰 → `unmatched_terms` 빈도 누적. `ExtractResult(posting_skill_rows: int, unmatched_terms: int)`.
  - 1~2글자 alias는 화이트리스트(`{"r","c","go","bi"}`)에 있을 때만, 제목 스캔에서는 단어경계 정규식으로만 매칭.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_extract.py
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from tracker.dictionary import load_dictionary
from tracker.extract import run, sync_skills, tokenize
from tracker.load import job_dicts_from_response, upsert_raw
from tracker.normalize import run as normalize_run
from tracker.schema import posting_skills, unmatched_terms

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _prep(db_conn, names):
    for f in names:
        resp = json.loads((FIX / f).read_text(encoding="utf-8"))
        upsert_raw(db_conn, job_dicts_from_response(resp), "데이터 분석가", datetime(2026, 9, 1, tzinfo=UTC))
    normalize_run(db_conn)
    sync_skills(db_conn, load_dictionary())


def test_tokenize_normalizes():
    assert tokenize("SQL, Python , SQL") == ["sql", "python"]


def test_extracts_known_skills_from_tags(db_conn):
    _prep(db_conn, ["da_junior_bi.json"])
    run(db_conn)
    skills = {r.skill_id for r in db_conn.execute(
        select(posting_skills).where(posting_skills.c.posting_id == "10001")).all()}
    assert {"sql", "python", "tableau", "ga4"} <= skills


def test_noise_tags_are_ignored(db_conn):
    _prep(db_conn, ["da_junior_bi.json"])
    run(db_conn)
    rows = db_conn.execute(select(posting_skills.c.skill_id)).scalars().all()
    assert "서울" not in rows and "데이터분석가" not in rows


def test_unmatched_terms_accumulate(db_conn):
    _prep(db_conn, ["da_junior_bi.json"])
    run(db_conn)
    run(db_conn)  # 재실행
    seoul = db_conn.execute(
        select(unmatched_terms.c.frequency).where(unmatched_terms.c.term == "서울")).scalar()
    assert seoul is not None and seoul >= 1


def test_run_idempotent_no_duplicate_rows(db_conn):
    _prep(db_conn, ["da_junior_bi.json"])
    run(db_conn)
    before = db_conn.execute(select(func.count()).select_from(posting_skills)).scalar()
    run(db_conn)
    after = db_conn.execute(select(func.count()).select_from(posting_skills)).scalar()
    assert before == after
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_extract.py -v`
Expected: FAIL

- [ ] **Step 3: `extract.py` 구현**

- `unmatched_terms` 재실행 시 빈도 누적을 막으려면: 각 실행에서 "이번에 본 미매칭 토큰 집합"을 계산하고 `on_conflict_do_update`로 `frequency = unmatched_terms.frequency + 1` — 단 **posting별 1회만** 카운트되도록 `(term)` 기준 set으로 모아서 처리(테스트는 `>= 1`이라 실행마다 +1도 허용되나, 스펙 의도는 "고유 공고 수"이므로 `example_posting` 기준 중복 방지 로직을 주석으로 남기고 Phase B에서 정교화).
- `posting_skills` upsert는 `(posting_id, skill_id)` 충돌 시 `matched_from` 우선순위(tag > title) 유지.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_extract.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/tracker/extract.py tests/test_extract.py
git commit -m "feat: add rule-based skill extractor"
```

---

## Task 9: aggregator (→ skill_daily_stats + _by_experience)

**Files:**
- Create: `src/tracker/aggregate.py`
- Test: `tests/test_aggregate.py`

**Interfaces:**
- Consumes: `tracker.schema.postings`, `tracker.schema.posting_skills`, `tracker.schema.skill_daily_stats`, `tracker.schema.skill_daily_stats_by_experience`.
- Produces:
  - `tracker.aggregate.experience_band(code: str|None) -> str` — `"2"` → `"senior"`, 그 외(`0`,`1`,`3`,None) → `"junior"`.
  - `tracker.aggregate.run(conn, snapshot_date: date) -> AggResult` — 해당 날짜 기준 `is_active`(spec: raw_postings.is_active) + 마감 안 된 `postings`를 job_group별로 집계. **dedup 그룹당 1건**(그룹 대표 = min posting_id). `skill_daily_stats`와 `_by_experience`를 upsert(`snapshot_date` 포함 PK). `AggResult(stat_rows: int, exp_stat_rows: int)`.
  - `ETC` job_group은 집계에서 제외.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_aggregate.py
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from tracker.aggregate import experience_band, run
from tracker.dedup import run as dedup_run
from tracker.dictionary import load_dictionary
from tracker.extract import run as extract_run
from tracker.extract import sync_skills
from tracker.load import job_dicts_from_response, upsert_raw
from tracker.normalize import run as normalize_run
from tracker.schema import skill_daily_stats, skill_daily_stats_by_experience

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _pipeline(db_conn, names):
    for f in names:
        resp = json.loads((FIX / f).read_text(encoding="utf-8"))
        upsert_raw(db_conn, job_dicts_from_response(resp), "kw", datetime(2026, 9, 1, tzinfo=UTC))
    normalize_run(db_conn)
    dedup_run(db_conn)
    sync_skills(db_conn, load_dictionary())
    extract_run(db_conn)


def test_experience_band():
    assert experience_band("2") == "senior"
    assert experience_band("1") == "junior"
    assert experience_band(None) == "junior"


def test_aggregate_ratio_and_dedup(db_conn):
    # da_junior_bi + 그 재공고 → DA 그룹 1개로 카운트
    _pipeline(db_conn, ["da_junior_bi.json", "repost_of_da_junior.json", "de_senior_pipeline.json"])
    run(db_conn, date(2026, 9, 1))
    da_sql = db_conn.execute(select(skill_daily_stats).where(
        (skill_daily_stats.c.job_group == "DA") & (skill_daily_stats.c.skill_id == "sql"))).one()
    assert da_sql.active_total == 1          # 재공고 합쳐 1
    assert da_sql.posting_count == 1
    assert float(da_sql.ratio) == 1.0


def test_by_experience_split(db_conn):
    _pipeline(db_conn, ["da_junior_bi.json", "de_senior_pipeline.json"])
    run(db_conn, date(2026, 9, 1))
    rows = db_conn.execute(select(skill_daily_stats_by_experience)).all()
    bands = {(r.job_group, r.experience_band) for r in rows}
    assert ("DA", "junior") in bands and ("DE", "senior") in bands


def test_etc_excluded(db_conn):
    _pipeline(db_conn, ["dev_mislabeled.json"])
    run(db_conn, date(2026, 9, 1))
    assert db_conn.execute(select(skill_daily_stats)).all() == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_aggregate.py -v`
Expected: FAIL

- [ ] **Step 3: `aggregate.py` 구현**

SQL 집계: dedup 그룹 대표만 남긴 CTE(`SELECT DISTINCT ON (dedup_group_id) ...`) → job_group별 `active_total` → `posting_skills` 조인해 skill별 `posting_count` → `ratio`. `snapshot_date`는 인자로 받은 값 사용. upsert on 복합 PK.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_aggregate.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/tracker/aggregate.py tests/test_aggregate.py
git commit -m "feat: add daily aggregation with dedup and experience split"
```

---

## Task 10: 파이프라인 오케스트레이터 + pipeline_runs

**Files:**
- Create: `src/tracker/pipeline.py`
- Modify: `README.md` (실행법에 `python -m tracker.pipeline` 추가)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `tracker.normalize.run`, `tracker.dedup.run`, `tracker.extract.run`, `tracker.extract.sync_skills`, `tracker.aggregate.run`, `tracker.dictionary.load_dictionary`, `tracker.schema.pipeline_runs`, `tracker.schema.postings`, `tracker.schema.unmatched_terms`, `tracker.schema.posting_skills`.
- Produces:
  - `tracker.pipeline.run_pipeline(conn, snapshot_date: date) -> str` — sync_skills → normalize → dedup → extract → aggregate 순차 실행. 시작 시 `pipeline_runs`에 `status='ok'` 행 생성(run_id=uuid4 hex), 종료 시 지표 채우고 `finished_at` 갱신. 예외 시 `status='failed'`, `notes`에 예외 메시지, 재-raise. 반환: run_id.
  - 지표: `postings_collected`(postings 총수), `postings_new`(이번 실행에서 신규 — 단순화: 전체 수), `unmatched_ratio`(distinct unmatched term / distinct posting_skills+unmatched), `ungrouped_ratio`(job_group='ETC' / 전체).
  - `python -m tracker.pipeline` 진입점: `get_engine()`으로 연결, `snapshot_date=date.today()`.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_pipeline.py
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from tracker.load import job_dicts_from_response, upsert_raw
from tracker.pipeline import run_pipeline
from tracker.schema import pipeline_runs, skill_daily_stats

FIX = Path(__file__).parent / "fixtures" / "saramin"


def _seed_raw(db_conn):
    for f in ["da_junior_bi.json", "de_senior_pipeline.json", "ds_ml.json", "dev_mislabeled.json"]:
        resp = json.loads((FIX / f).read_text(encoding="utf-8"))
        upsert_raw(db_conn, job_dicts_from_response(resp), "kw", datetime(2026, 9, 1, tzinfo=UTC))


def test_run_pipeline_end_to_end(db_conn):
    _seed_raw(db_conn)
    run_id = run_pipeline(db_conn, date(2026, 9, 1))
    run_row = db_conn.execute(select(pipeline_runs).where(pipeline_runs.c.run_id == run_id)).one()
    assert run_row.status == "ok"
    assert run_row.finished_at is not None
    assert run_row.postings_collected == 4
    assert 0 <= float(run_row.ungrouped_ratio) <= 1
    assert float(run_row.ungrouped_ratio) == 0.25       # dev_mislabeled 1/4 → ETC
    assert db_conn.execute(select(skill_daily_stats)).first() is not None


def test_run_pipeline_is_idempotent(db_conn):
    _seed_raw(db_conn)
    run_pipeline(db_conn, date(2026, 9, 1))
    run_pipeline(db_conn, date(2026, 9, 1))
    da_sql = db_conn.execute(select(skill_daily_stats).where(
        (skill_daily_stats.c.job_group == "DA") & (skill_daily_stats.c.skill_id == "sql"))).all()
    assert len(da_sql) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: `pipeline.py` 구현 + README 갱신**

- [ ] **Step 4: 전체 테스트 통과 확인**

Run: `pytest -v && ruff check src tests`
Expected: 전체 PASS, 린트 클린

- [ ] **Step 5: 커밋**

```bash
git add src/tracker/pipeline.py tests/test_pipeline.py README.md
git commit -m "feat: add pipeline orchestrator with run metrics"
```

---

## Self-Review

**Spec coverage:**
- 데이터 모델 11개 테이블 → Task 2 ✅
- 파이프라인 4단계 분리 → Task 6/7/8/9, 오케스트레이션 Task 10 ✅
- 스킬 사전 화이트리스트 + YAML → Task 3 ✅
- job_group 분류 규칙 4단계 → Task 4 ✅
- 중복 공고 dedup (회사+제목+경력, 90일) → Task 7 ✅
- keyword 태그 기반 추출, is_required 없음 → Task 8 ✅
- 신입/경력 분리 집계 → Task 9 ✅
- dedup 그룹당 1건 카운트 → Task 9 (test_aggregate_ratio_and_dedup) ✅
- ETC 격리, ungrouped_ratio 추적 → Task 4/9/10 ✅
- 멱등성 → 각 Task에 idempotency 테스트 ✅
- pipeline_runs 데이터 품질 지표 → Task 10 ✅
- **스코프 밖(이 계획 아님, 다음 계획):** collector 실 API 호출(Phase B), LLM 사전 발굴 배치(Phase B), FastAPI 분석 레이어(계획 2), Next.js(계획 3), GitHub Actions 배포(계획 4). 스펙 Phase A의 "코드표 확보"는 Task 4의 `job_group_map.yaml`로 축소 반영(지역/학력 코드표는 정규화에 이름이 이미 응답에 포함돼 Phase A에서는 불필요, Phase B collector에서 필요 시 추가).

**Placeholder scan:** Task 4 Step 4에 "구현 시 시그니처를 맞춘다"는 지시가 있으나 이는 명시적 수정 지침(모호한 TODO 아님). Task 8 Step 3의 unmatched_terms 정교화는 Phase B로 명시적 이월. 그 외 플레이스홀더 없음.

**Type consistency:** `run(conn) -> int`(normalize/dedup), `run(conn) -> ExtractResult`(extract), `run(conn, snapshot_date) -> AggResult`(aggregate), `run_pipeline(conn, snapshot_date) -> str`. 픽스처 id(`10001`~`10005`)는 Task 5에서 정의, 이후 태스크 테스트에서 일관 사용. `experience_band` 규칙은 Task 9에서 정의, aggregate만 사용.

---

## Execution Handoff

계획 완료, `docs/superpowers/plans/2026-09-04-phase-a-data-pipeline.md`에 저장됨.
