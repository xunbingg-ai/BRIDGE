# BRIDGE Session 2026-08-18: feat-011 (DeepSeek provider) + feat-010 (Case data model & seed workflow) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 本次 session 完成 feat-011（DeepSeek V4 Flash 适配层，真实 key 连通验证）与 feat-010（病例数据模型 + 开发者录入/种子工作流，Cecilia 病例入库），全部验收通过并提交。

**Architecture:** 后端 FastAPI + SQLAlchemy 2.0 + Alembic；LLM 走 OpenAI 兼容客户端（`openai` SDK，base_url 指向 DeepSeek，模型 `deepseek-v4-flash`），key 只从 `backend/.env` / 环境变量读取并保证 git 忽略。病例以 JSON 文件 + Pydantic 强类型 schema 录入，种子脚本幂等导入 SQLite。SP 对话、评分、SSE 流式三个模块依赖同一个 LLM 客户端（依赖注入，测试用 mock）。

**Tech Stack:** Python 3.12+（WSL 内 uv 管理）、FastAPI、SQLAlchemy 2.0、Alembic、Pydantic v2（pydantic-settings）、openai>=1.50、pytest + httpx。

**Spec:**
- `docs/TASK-BREAKDOWN.md` — T-010.1~T-010.5、T-011.1~T-011.4 验收标准
- `BRIDGE - 首期需求文档.md` §6–§9 — 病例数据字段与 CCE 流程
- `Example teaching case.md` — Cecilia（GP-ChestPain-0001）种子数据唯一来源
- `CONTEXT.md` — 术语（Case / SP / Section / Structured Question / Investigation Result / Rubric / Language Rule）
- `docs/adr/0002-de-identification-and-privacy.md`、`docs/adr/0004-deepseek-provider.md`
- `feature_list.json` — 特性状态唯一事实源

## Global Constraints

- 模型 ID 固定为 `deepseek-v4-flash`；base URL 固定为 `https://api.deepseek.com`（来自 ADR-0004）。
- API key 只从 `DEEPSEEK_API_KEY` 环境变量或 `backend/.env` 读取，**永不硬编码**、永不打印、永不提交 git。`backend/.env` 必须被 `.gitignore` 忽略（git check-ignore 验证）。
- `backend/.env.example` 允许提交（.gitignore 需要 `!**/.env.example` 反规则）；`*.db` 加入 .gitignore（SQLite 数据库文件不提交）。
- 病例内容**不写入应用日志**（ADR-0002）。
- 语言规则：Case 上配置 `languageAvailability`（对外展示）与 `sections_language`（每 section 语言，key ∈ {student_instruction, history_taking, case_presentation, structured_questions, scoring}，value ∈ {en, zh}）。**首期演示为中文版（2026-08-18 用户决策）：Cecilia 病例 `sections_language` 全部为 `zh`，病例内容翻译为中文；平台 UI 仍为英文（ADR-0001）**。
- 脱敏：**本期不实现自动脱敏校验**（2026-08-18 用户决策：首期病例全部为虚拟病例；日后加入真实病例时由用户亲自校验；ADR-0002 政策保留）。schema 中仅以注释记录该政策，不写校验器。
- 术语遵守 `CONTEXT.md`：模型命名用 Case、PatientInformation、ExaminerPack、CaseReviewRecord、Rubric、Practice Session 等规范词。
- 一次只做一个 feature（AGENTS.md），但执行顺序按用户 2026-08-18 明确要求：**先打通 DeepSeek 真实调用（T-011.1 前置）→ 再做 feat-010 → 最后完成 T-011.2~T-011.4**。
- 所有命令在 WSL（Ubuntu 2）中执行：`cd /mnt/d/BRIDGE && ...`。

## Test Seams（tdd skill 要求：写测试前与用户确认的公开边界）

以下接缝已列入计划各任务，测试只在这些公开边界上进行（不测内部实现）：

1. **LLM 客户端**（Task 1）：`build_llm_client()` 与 `model_name()` — 通过 mock HTTP transport 验证 base_url/model 调用参数；无 key 时报 `LLMConfigError`。
2. **领域模型**（Task 2）：`Case`/`PatientInformation`/`ExaminerPack`/`CaseReviewRecord` — 通过 SQLAlchemy ORM 公开接口验证持久化、一对一关系、级联删除、唯一约束。
3. **病例文件 schema**（Task 4）：`cases.schema.CaseFile.model_validate(...)` — 合法文件通过；缺字段/未知 section key/非法枚举/空问题列表被拒。
4. **种子导入**（Task 5/6）：`seed_cases(cases_dir, engine)` — 导入成功、幂等、多文件、非法文件不污染数据库、重复导入反映文件变更。
5. **SP 对话模块**（Task 7）：`build_sp_messages(...)` 的 prompt 内容（含脚本与约束文案）+ `SPResponder.respond(...)` 以 fake client 验证调用参数与返回文本。
6. **评分模块**（Task 8）：`Scorer.score(...)` 以 fake client 验证合法 JSON 解析、无 rubric 拒绝、非法 JSON 报错。
7. **SSE 端点**（Task 9）：`POST /api/chat/stream` 以 fake client 验证状态码 200、`text/event-stream`、首个事件与 `[DONE]`。

（用户 2026-08-18 已同意上述接缝；若需增删，在开工前提出。）

## File Structure

```
backend/
  .env.example                      # 新建，可提交（占位 key）
  pyproject.toml                    # 修改：+ alembic
  app/
    core/config.py                  # 修改：+ deepseek_base_url/deepseek_model
    models/
      __init__.py                   # 新建：导出 Base 与全部模型
      base.py                       # 新建：DeclarativeBase + TimestampMixin
      case.py                       # 新建：Case/PatientInformation/ExaminerPack/CaseReviewRecord
    services/
      llm/__init__.py               # 新建
      llm/client.py                 # 新建：build_llm_client()/model_name()/LLMConfigError
      sp/__init__.py                # 新建
      sp/patient.py                 # 新建：SPResponder + build_sp_messages
      scoring/__init__.py           # 新建
      scoring/schemas.py            # 新建：ScoreResult
      scoring/scorer.py             # 新建：Scorer + NoRubricError + InvalidScoreOutputError
    prompts/
      sp_system.txt                 # 新建：SP 角色约束
      sp_user.txt                   # 新建：脚本+历史+当前提问
      scoring_system.txt            # 新建：评分 JSON 输出约束
      scoring_user.txt              # 新建：rubric+学生作答
    api/
      chat.py                       # 新建：POST /api/chat/stream（SSE）
  cases/
    schema.py                       # 新建：CaseFile 等 Pydantic 模型
    GP-ChestPain-0001.json          # 新建：Cecilia 种子数据
  scripts/
    smoke_llm.py                    # 新建：真实 key 连通性验证
    seed_cases.py                   # 新建：幂等导入脚本
  alembic/                          # 新建（alembic init 生成 + env.py 修改 + 首个迁移）
  tests/
    test_llm_client.py              # 新建
    test_models.py                  # 新建
    test_case_schema.py             # 新建
    test_seed_cases.py              # 新建
    test_sp_patient.py              # 新建
    test_scoring.py                 # 新建
    test_chat_stream.py             # 新建
.gitignore                          # 修改：!**/.env.example、*.db
init.sh                             # 修改：密钥卫生检查（git check-ignore + git ls-files）
docs/case-file-format.md            # 新建：字段与 Excel 模板/§9 对应关系
docs/superpowers/plans/2026-08-18-feat-010-011-case-model-and-llm.md  # 本计划
```

---

## Task 1: 密钥卫生 + LLM 客户端前置（T-011.1 + 安全）

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/llm/__init__.py`、`backend/app/services/llm/client.py`、`backend/scripts/smoke_llm.py`、`backend/.env.example`
- Modify: `.gitignore`、`init.sh`
- Test: `backend/tests/test_llm_client.py`

**Interfaces:**
- Produces: `app.core.config.Settings` 新增字段 `deepseek_api_key: str`、`deepseek_base_url: str = "https://api.deepseek.com"`、`deepseek_model: str = "deepseek-v4-flash"`（`deepseek_api_key` 已存在，仅确认）
- Produces: `app.services.llm.client.build_llm_client(http_client: httpx.Client | None = None) -> AsyncOpenAI`；`model_name() -> str`；`LLMConfigError(RuntimeError)`
- Produces: `backend/scripts/smoke_llm.py`（`uv run python scripts/smoke_llm.py` 退出码 0=成功）

- [ ] **Step 1: 修改 `backend/app/core/config.py` 增加 DeepSeek 配置**

```python
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
```

- [ ] **Step 2: 新建 `backend/app/services/llm/client.py`**

```python
"""DeepSeek (OpenAI-compatible) async client factory.

The API key is read from settings (DEEPSEEK_API_KEY env var / backend/.env).
Never hardcode credentials here. Never log the key.
"""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class LLMConfigError(RuntimeError):
    """Raised when the LLM is used without a configured API key."""


def build_llm_client(http_client: httpx.Client | None = None) -> AsyncOpenAI:
    if not settings.deepseek_api_key:
        raise LLMConfigError(
            "DEEPSEEK_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and fill in your key (backend/.env is git-ignored)."
        )
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        http_client=http_client,
    )


def model_name() -> str:
    return settings.deepseek_model
```

（`app/services/llm/__init__.py` 留空即可。）

- [ ] **Step 3: 新建 `backend/scripts/smoke_llm.py`（不打印 key）**

```python
"""One-shot live check that the DeepSeek API key works.

Usage (WSL, from backend/): uv run python scripts/smoke_llm.py
Prints only the model reply — never the API key.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm.client import build_llm_client, model_name  # noqa: E402


async def main() -> int:
    try:
        client = build_llm_client()
        resp = await client.chat.completions.create(
            model=model_name(),
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=16,
        )
    except Exception as exc:  # surface any upstream failure clearly
        print(f"SMOKE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("SMOKE OK")
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 4: 新建 `backend/.env.example` 并修改 `.gitignore`**

`backend/.env.example`：
```
# Copy this file to backend/.env and fill in your key.
# backend/.env is git-ignored — never commit the real key.
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.gitignore` 追加：
```
# Allow committed example templates (real .env files stay ignored)
!**/.env.example

# Local SQLite databases
*.db
*.db-journal
```

- [ ] **Step 5: 修改 `init.sh`，在验证前加密钥卫生检查**

在 `cd "$(dirname "$0")"` 之后插入：
```bash
echo "=== Secret hygiene check ==="
if ! git check-ignore -q backend/.env; then
  echo "FATAL: backend/.env is NOT git-ignored; refusing to continue" >&2
  exit 1
fi
if [ -n "$(git ls-files backend/.env)" ]; then
  echo "FATAL: backend/.env is tracked by git; remove it first" >&2
  exit 1
fi
echo "backend/.env is git-ignored (OK)"
```

- [ ] **Step 6: 新建 `backend/tests/test_llm_client.py`（mock 传输验证 base_url/model）**

```python
import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.services.llm import client as llm_client


def _fake_completion_body() -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1728000000,
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "OK"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def test_client_hits_deepseek_endpoint_with_model(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["payload"] = request.content
        return httpx.Response(200, json=_fake_completion_body())

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        llm_client,
        "settings",
        Settings(_env_file=None, deepseek_api_key="sk-test"),
    )

    client = llm_client.build_llm_client(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    async def _run():
        resp = await client.chat.completions.create(
            model=llm_client.model_name(),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
        )
        return resp.choices[0].message.content

    assert asyncio.run(_run()) == "OK"
    assert seen["url"].startswith("https://api.deepseek.com")
    assert b"deepseek-v4-flash" in seen["payload"]


def test_build_llm_client_raises_without_key(monkeypatch):
    monkeypatch.setattr(
        llm_client, "settings", Settings(_env_file=None, deepseek_api_key="")
    )
    with pytest.raises(llm_client.LLMConfigError):
        llm_client.build_llm_client()
```

- [ ] **Step 7: 运行测试并验证密钥卫生**

```bash
cd /mnt/d/BRIDGE && bash init.sh
```
期望：Secret hygiene check 输出 `backend/.env is git-ignored (OK)`；pytest 全绿（含 2 个新测试）。

- [ ] **Step 8: 用户创建 `backend/.env` 并运行真实 smoke 验证**

用户把 key 填入 `backend/.env` 后执行：
```bash
cd /mnt/d/BRIDGE/backend && uv run python scripts/smoke_llm.py
```
期望输出：`SMOKE OK` + 模型回复（如 `OK`）。这一步必须真实成功后才能进入 Task 2（用户要求）。

- [ ] **Step 9: 提交**

```bash
git add .gitignore init.sh backend/.env.example backend/pyproject.toml backend/uv.lock backend/app/core/config.py backend/app/services/llm backend/scripts/smoke_llm.py backend/tests/test_llm_client.py
git commit -m "feat(011): LLM client + env preflight (key from backend/.env, git-ignored; smoke script)"
```

---

## Task 2: feat-010 T-010.1 领域数据模型

**Files:**
- Create: `backend/app/models/__init__.py`、`backend/app/models/base.py`、`backend/app/models/case.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `app.models.Base`（DeclarativeBase）、`app.models.TimestampMixin`、`app.models.CaseType`（initial_visit|follow_up_visit）、`app.models.CaseStatus`（draft|in_review|approved|published）
- Produces: 模型 `Case`（主键 `id` = case_id）、`PatientInformation`（case_id 唯一外键，一对一）、`ExaminerPack`（case_id 唯一外键，一对一）、`CaseReviewRecord`（case_id 唯一外键，可空）
- Consumes: 无（独立）；Task 4 的 `cases/schema.py` 与其字段一一对应

- [ ] **Step 1: 新建 `backend/app/models/base.py`**

```python
"""Declarative base and common mixins for BRIDGE models."""
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: 新建 `backend/app/models/case.py`（字段与需求 §9 一一对应，含映射注释）**

```python
"""Case domain models — field mapping to requirements doc section 9.

Case.id             -> Case.id / Case ID
Case.title          -> Case.title
Case.type           -> Case.type (initial_visit | follow_up_visit)
Case.system_tags    -> Case.systemTags
Case.difficulty     -> Case.difficulty
Case.language_availability -> Case.languageAvailability
Case.sections_language      -> requirements section 7 per-section Language Rule
Case.learning_objectives    -> Case.learningObjectives
Case.student_instructions   -> Case.studentInstructions
Case.status         -> Case.status (draft | in_review | approved | published)
PatientInformation  -> requirements section 9.2 (all fields)
ExaminerPack        -> requirements section 9.3 (all fields)
CaseReviewRecord    -> requirements section 9.4 (all fields)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CaseType(str, Enum):
    initial_visit = "initial_visit"
    follow_up_visit = "follow_up_visit"


class CaseStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[CaseType] = mapped_column(SqlEnum(CaseType))
    system_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(40))
    language_availability: Mapped[list[str]] = mapped_column(JSON, default=list)
    sections_language: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    learning_objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    student_instructions: Mapped[str] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        SqlEnum(CaseStatus), default=CaseStatus.draft
    )

    patient_information: Mapped[PatientInformation] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    examiner_pack: Mapped[ExaminerPack] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    review_record: Mapped[CaseReviewRecord | None] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )


class PatientInformation(TimestampMixin, Base):
    __tablename__ = "patient_information"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(80))
    age: Mapped[int] = mapped_column()
    gender: Mapped[str] = mapped_column(String(20))
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    patient_language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    chief_complaint: Mapped[str] = mapped_column(Text)
    history_of_present_illness: Mapped[str] = mapped_column(Text)
    review_of_systems: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    past_medical_history: Mapped[list[str]] = mapped_column(JSON, default=list)
    past_surgical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[list[str]] = mapped_column(JSON, default=list)
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_social_history: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    sexual_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    obgyn_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_statement: Mapped[str] = mapped_column(Text)
    affect_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    ice: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    disclosure_rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    qa_triggers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    default_negative_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship(back_populates="patient_information")


class ExaminerPack(TimestampMixin, Base):
    __tablename__ = "examiner_packs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    case_summary: Mapped[str] = mapped_column(Text)
    working_diagnosis: Mapped[str] = mapped_column(Text)
    differentials: Mapped[list[str]] = mapped_column(JSON, default=list)
    structured_questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    suggested_answers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    physical_exam_release: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    investigation_release: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scoring_rubric: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    case: Mapped[Case] = relationship(back_populates="examiner_pack")


class CaseReviewRecord(TimestampMixin, Base):
    __tablename__ = "case_review_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    review_status: Mapped[str] = mapped_column(String(40))
    reviewer_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped[Case] = relationship(back_populates="review_record")
```

- [ ] **Step 3: 新建 `backend/app/models/__init__.py`**

```python
"""ORM models — import everything so Base.metadata is complete."""
from app.models.base import Base, TimestampMixin
from app.models.case import (
    Case,
    CaseReviewRecord,
    CaseStatus,
    CaseType,
    ExaminerPack,
    PatientInformation,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "Case",
    "CaseReviewRecord",
    "CaseStatus",
    "CaseType",
    "ExaminerPack",
    "PatientInformation",
]
```

- [ ] **Step 4: 新建 `backend/tests/test_models.py`**

```python
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Case, CaseStatus, CaseType, ExaminerPack, PatientInformation


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_case():
    return Case(
        id="GP-ChestPain-0001",
        title="Stress-related chest pain",
        type=CaseType.initial_visit,
        system_tags=["primary-care", "cardiology"],
        difficulty="medium",
        language_availability=["en"],
        sections_language={
            "student_instruction": "en",
            "history_taking": "en",
            "case_presentation": "en",
            "structured_questions": "en",
            "scoring": "en",
        },
        learning_objectives=["approach to chest pain in primary care"],
        student_instructions="Take a focused history.",
        status=CaseStatus.published,
        patient_information=PatientInformation(
            name="Ms. Chen",
            age=32,
            gender="female",
            chief_complaint="Recurrent chest pain for 4 weeks.",
            history_of_present_illness="Intermittent sharp pain.",
            opening_statement="I have had chest pain on and off for 4 weeks.",
        ),
        examiner_pack=ExaminerPack(
            case_summary="32yo woman with recurrent chest pain.",
            working_diagnosis="Stress/anxiety-related chest pain",
            differentials=["Angina", "Costochondritis"],
            structured_questions=[
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "State the most likely diagnosis.",
                    "language": "en",
                }
            ],
            suggested_answers=[{"question_id": "sq-1", "answer": "Stress-related chest pain."}],
            physical_exam_release=[],
            investigation_release=[],
            scoring_rubric={"max_score": 100, "criteria": []},
        ),
    )


def test_case_persists_with_related_objects(session):
    session.add(_make_case())
    session.commit()

    case = session.scalars(select(Case)).one()
    assert case.patient_information.name == "Ms. Chen"
    assert case.examiner_pack.working_diagnosis == "Stress/anxiety-related chest pain"
    assert case.status == CaseStatus.published
    assert len(case.examiner_pack.structured_questions) == 1


def test_patient_information_is_one_to_one(session):
    session.add(_make_case())
    session.commit()

    case = session.scalars(select(Case)).one()
    session.add(
        PatientInformation(
            case_id=case.id,
            name="Duplicate",
            age=30,
            gender="female",
            chief_complaint="x",
            history_of_present_illness="y",
            opening_statement="z",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_case_cascades_to_children(session):
    session.add(_make_case())
    session.commit()
    case = session.scalars(select(Case)).one()
    session.delete(case)
    session.commit()
    assert session.scalars(select(PatientInformation)).all() == []
    assert session.scalars(select(ExaminerPack)).all() == []
```

- [ ] **Step 5: 运行测试**

```bash
cd /mnt/d/BRIDGE/backend && uv run pytest -q
```
期望：3 个新测试通过（与已有 1 个合计 4 passed）。

---

## Task 3: feat-010 T-010.2 Alembic 迁移

**Files:**
- Modify: `backend/pyproject.toml`（+ `alembic`）
- Create: `backend/alembic/`（`uv run alembic init alembic` 生成后修改 `env.py`）
- Create: `backend/alembic/versions/xxxx_initial_case_tables.py`（autogenerate）

**Interfaces:**
- Consumes: `app.models.Base`（Task 2）、`app.core.config.settings.database_url`
- Produces: 首个可重复迁移；`uv run alembic upgrade head` / `downgrade base` 往返无损

- [ ] **Step 1: 添加 alembic 依赖**

```bash
cd /mnt/d/BRIDGE/backend && uv add alembic
```

- [ ] **Step 2: 初始化并接线**

```bash
uv run alembic init alembic
```

修改 `backend/alembic/env.py`：
```python
from app.core.config import settings
from app.models import Base

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

- [ ] **Step 3: 生成首个迁移并验证往返**

```bash
uv run alembic revision --autogenerate -m "initial case tables"
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```
期望：三次命令均成功，无 SQL 报错；`backend/bridge.db` 出现且被 .gitignore 忽略（`git check-ignore -v bridge.db` 命中 `*.db`）。

- [ ] **Step 4: 提交**

```bash
git add backend/pyproject.toml backend/uv.lock backend/alembic backend/app/models
git commit -m "feat(010): domain models + initial Alembic migration (case tables)"
```

---

## Task 4: feat-010 T-010.3 病例文件 schema + 格式文档

**Files:**
- Create: `backend/cases/schema.py`
- Create: `docs/case-file-format.md`
- Test: `backend/tests/test_case_schema.py`

**Interfaces:**
- Produces: `cases.schema.CaseFile`（Pydantic 根模型）、`PatientInfoFile`、`ExaminerPackFile`、`StructuredQuestionFile`、`SuggestedAnswerFile`、`ReleaseItemFile`、`ScoringRubricFile`、`CaseReviewRecordFile`
- Consumes: 无；Task 5 的种子脚本用 `CaseFile.model_validate`
- 约束：字段与 `docs/case-file-format.md` 一一对应；**不做脱敏校验**（用户 2026-08-18 决策，schema 顶部注释记录 ADR-0002 政策）

- [ ] **Step 1: 新建 `backend/cases/schema.py`**

```python
"""Pydantic schema for developer-authored case JSON files (phase 1).

Field mapping to the requirements doc section 9 and the Excel template is
documented in docs/case-file-format.md.

NOTE (2026-08-18 user decision): de-identification validation is intentionally
NOT implemented in phase 1 because all phase-1 cases are fictional. ADR-0002
still applies: real-patient cases must be de-identified by the user personally
before entering the library.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CaseType(str, Enum):
    initial_visit = "initial_visit"
    follow_up_visit = "follow_up_visit"


class CaseStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"


class Language(str, Enum):
    en = "en"
    zh = "zh"


SECTION_KEYS = {
    "student_instruction",
    "history_taking",
    "case_presentation",
    "structured_questions",
    "scoring",
}


class PatientInfoFile(BaseModel):
    name: str
    age: int = Field(ge=0, le=120)
    gender: str
    occupation: str | None = None
    ethnicity: str | None = None
    patient_language: str | None = None
    chief_complaint: str
    history_of_present_illness: str
    review_of_systems: dict[str, str] = Field(default_factory=dict)
    past_medical_history: list[str] = Field(default_factory=list)
    past_surgical_history: str | None = None
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    family_history: str | None = None
    personal_social_history: dict[str, str] = Field(default_factory=dict)
    sexual_history: str | None = None
    obgyn_history: str | None = None
    opening_statement: str
    affect_style: str | None = None
    ice: dict[str, str] = Field(default_factory=dict)
    disclosure_rules: list[str] = Field(default_factory=list)
    qa_triggers: list[dict[str, Any]] = Field(default_factory=list)
    default_negative_response: str | None = None


class StructuredQuestionFile(BaseModel):
    id: str
    order: int = Field(ge=1)
    question: str
    language: Language
    reveal_items: list[str] = Field(default_factory=list)


class SuggestedAnswerFile(BaseModel):
    question_id: str
    answer: str


class ReleaseItemFile(BaseModel):
    item_id: str
    name: str
    result: str
    reference_range: str | None = None


class ScoringRubricFile(BaseModel):
    max_score: int = Field(gt=0, default=100)
    criteria: list[dict[str, Any]] = Field(default_factory=list)


class ExaminerPackFile(BaseModel):
    case_summary: str
    working_diagnosis: str
    differentials: list[str] = Field(default_factory=list)
    structured_questions: list[StructuredQuestionFile] = Field(min_length=1)
    suggested_answers: list[SuggestedAnswerFile] = Field(default_factory=list)
    physical_exam_release: list[ReleaseItemFile] = Field(default_factory=list)
    investigation_release: list[ReleaseItemFile] = Field(default_factory=list)
    scoring_rubric: ScoringRubricFile | None = None


class CaseReviewRecordFile(BaseModel):
    review_status: str
    reviewer_name: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    published_at: datetime | None = None


class CaseFile(BaseModel):
    case_id: str = Field(min_length=1)
    title: str
    type: CaseType
    system_tags: list[str] = Field(default_factory=list)
    difficulty: str
    language_availability: list[Language] = Field(default_factory=list)
    sections_language: dict[str, Language]
    learning_objectives: list[str] = Field(default_factory=list)
    student_instructions: str
    status: CaseStatus = CaseStatus.draft
    patient_information: PatientInfoFile
    examiner_pack: ExaminerPackFile
    review_record: CaseReviewRecordFile | None = None

    @field_validator("sections_language")
    @classmethod
    def _check_section_keys(cls, v: dict[str, Language]) -> dict[str, Language]:
        unknown = set(v) - SECTION_KEYS
        if unknown:
            raise ValueError(f"unknown section keys: {sorted(unknown)}")
        return v
```

- [ ] **Step 2: 新建 `docs/case-file-format.md`（字段↔Excel/§9 对应表）**

文档必须包含：JSON 顶层字段与需求 §9 的 Case/PatientInformation/ExaminerPack/CaseReviewRecord 对应表；`sections_language` 的合法 key/value；`structured_questions[].reveal_items` 语义（对应 physical_exam_release/investigation_release 的 item_id，供 feat-007 使用）；rubric 可缺省（缺省则该病例不给 AI 分数）；顶部注明脱敏政策（本期虚拟病例不校验，真实病例由用户亲自校验）。

- [ ] **Step 3: 新建 `backend/tests/test_case_schema.py`**

```python
import pytest
from pydantic import ValidationError

from cases.schema import CaseFile


def _valid_payload() -> dict:
    return {
        "case_id": "GP-ChestPain-0001",
        "title": "Stress-related chest pain",
        "type": "initial_visit",
        "system_tags": ["primary-care"],
        "difficulty": "medium",
        "language_availability": ["en"],
        "sections_language": {
            "student_instruction": "en",
            "history_taking": "en",
            "case_presentation": "en",
            "structured_questions": "en",
            "scoring": "en",
        },
        "learning_objectives": ["approach to chest pain"],
        "student_instructions": "Take a focused history.",
        "status": "published",
        "patient_information": {
            "name": "Ms. Chen",
            "age": 32,
            "gender": "female",
            "chief_complaint": "Recurrent chest pain for 4 weeks.",
            "history_of_present_illness": "Intermittent sharp pain.",
            "opening_statement": "I have had chest pain for 4 weeks.",
        },
        "examiner_pack": {
            "case_summary": "32yo woman with chest pain.",
            "working_diagnosis": "Stress-related chest pain",
            "differentials": ["Angina"],
            "structured_questions": [
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "State the most likely diagnosis.",
                    "language": "en",
                    "reveal_items": [],
                }
            ],
            "suggested_answers": [
                {"question_id": "sq-1", "answer": "Stress-related chest pain."}
            ],
            "physical_exam_release": [],
            "investigation_release": [],
            "scoring_rubric": {"max_score": 100, "criteria": []},
        },
    }


def test_valid_case_file_parses():
    case = CaseFile.model_validate(_valid_payload())
    assert case.case_id == "GP-ChestPain-0001"
    assert case.status == "published"
    assert case.examiner_pack.structured_questions[0].id == "sq-1"


def test_missing_required_field_rejected():
    payload = _valid_payload()
    del payload["title"]
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_unknown_section_key_rejected():
    payload = _valid_payload()
    payload["sections_language"]["scoring_extra"] = "en"
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_bad_enum_rejected():
    payload = _valid_payload()
    payload["type"] = "emergency"
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_empty_structured_questions_rejected():
    payload = _valid_payload()
    payload["examiner_pack"]["structured_questions"] = []
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)
```

- [ ] **Step 4: 运行测试**

```bash
cd /mnt/d/BRIDGE/backend && uv run pytest -q
```
期望：5 个新测试通过。

---

## Task 5: feat-010 T-010.4 种子脚本 + Cecilia 病例

**Files:**
- Create: `backend/scripts/seed_cases.py`
- Create: `backend/cases/GP-ChestPain-0001.json`

**Interfaces:**
- Produces: `seed_cases(cases_dir: Path, engine: Engine) -> list[str]`（返回导入的 case_id 列表；幂等：重复运行结果一致）
- Produces: `backend/scripts/seed_cases.py` CLI：`uv run python scripts/seed_cases.py [cases_dir] [database_url]`
- Consumes: `cases.schema.CaseFile`（Task 4）、`app.models`（Task 2）

- [ ] **Step 1: 新建 `backend/scripts/seed_cases.py`**

```python
"""Idempotent case importer for developer-authored JSON files.

Usage (WSL, from backend/):
    uv run python scripts/seed_cases.py                 # default: ./cases + settings.database_url
    uv run python scripts/seed_cases.py ./cases sqlite:///./bridge.db

Loading is atomic per run: if any file fails validation, nothing is committed.
"""
import json
import sys
from pathlib import Path

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    Case,
    CaseReviewRecord,
    ExaminerPack,
    PatientInformation,
)
from cases.schema import CaseFile  # noqa: E402


def _build_orm(case_file: CaseFile) -> Case:
    case = Case(
        id=case_file.case_id,
        title=case_file.title,
        type=case_file.type,
        system_tags=case_file.system_tags,
        difficulty=case_file.difficulty,
        language_availability=[lang.value for lang in case_file.language_availability],
        sections_language={
            key: lang.value for key, lang in case_file.sections_language.items()
        },
        learning_objectives=case_file.learning_objectives,
        student_instructions=case_file.student_instructions,
        status=case_file.status,
    )
    p = case_file.patient_information
    case.patient_information = PatientInformation(
        name=p.name,
        age=p.age,
        gender=p.gender,
        occupation=p.occupation,
        ethnicity=p.ethnicity,
        patient_language=p.patient_language,
        chief_complaint=p.chief_complaint,
        history_of_present_illness=p.history_of_present_illness,
        review_of_systems=p.review_of_systems,
        past_medical_history=p.past_medical_history,
        past_surgical_history=p.past_surgical_history,
        medications=p.medications,
        allergies=p.allergies,
        family_history=p.family_history,
        personal_social_history=p.personal_social_history,
        sexual_history=p.sexual_history,
        obgyn_history=p.obgyn_history,
        opening_statement=p.opening_statement,
        affect_style=p.affect_style,
        ice=p.ice,
        disclosure_rules=p.disclosure_rules,
        qa_triggers=p.qa_triggers,
        default_negative_response=p.default_negative_response,
    )
    e = case_file.examiner_pack
    case.examiner_pack = ExaminerPack(
        case_summary=e.case_summary,
        working_diagnosis=e.working_diagnosis,
        differentials=e.differentials,
        structured_questions=[q.model_dump() for q in e.structured_questions],
        suggested_answers=[a.model_dump() for a in e.suggested_answers],
        physical_exam_release=[r.model_dump() for r in e.physical_exam_release],
        investigation_release=[r.model_dump() for r in e.investigation_release],
        scoring_rubric=(
            e.scoring_rubric.model_dump() if e.scoring_rubric is not None else None
        ),
    )
    if case_file.review_record is not None:
        r = case_file.review_record
        case.review_record = CaseReviewRecord(
            review_status=r.review_status,
            reviewer_name=r.reviewer_name,
            review_comment=r.review_comment,
            reviewed_at=r.reviewed_at,
            published_at=r.published_at,
        )
    return case


def _upsert(session: Session, case_file: CaseFile) -> None:
    existing = session.get(Case, case_file.case_id)
    if existing is not None:
        session.delete(existing)
        session.flush()
    session.add(_build_orm(case_file))


def seed_cases(cases_dir: Path, engine: Engine) -> list[str]:
    Base.metadata.create_all(engine)
    imported: list[str] = []
    with Session(engine) as session:
        for path in sorted(cases_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_file = CaseFile.model_validate(payload)
            _upsert(session, case_file)
            imported.append(case_file.case_id)
        session.commit()
    return imported


def main() -> int:
    cases_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "cases"
    database_url = sys.argv[2] if len(sys.argv) > 2 else settings.database_url
    engine = create_engine(database_url)
    imported = seed_cases(cases_dir, engine)
    print(f"Imported {len(imported)} case(s): {', '.join(imported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 生成 `backend/cases/GP-ChestPain-0001.json`**

数据来源唯一为 `Example teaching case.md`，逐段转写并翻译为中文（医学内容不变，仅语言转换；禁止改写医学事实）：

| JSON 字段 | 来源（Example teaching case.md） |
|---|---|
| case_id / title / type | §1（GP-ChestPain-0001；title 原文；type=initial_visit） |
| system_tags | 依据内容自定：`["primary-care", "cardiology", "psychosocial"]` |
| difficulty | 自定为 `"medium"`（首期无更细标准） |
| language_availability | `["zh"]`（2026-08-18 用户决策：首期演示中文版） |
| sections_language | 全部 `"zh"`（病例内容为中文翻译） |
| learning_objectives | §1 Key learning objective |
| student_instructions | §2.1 Patient Background + §2.2 Student Tasks 原文 |
| status | `"published"` |
| patient_information.name | §3 Patient Code：虚构代号，中文版用 `"陈女士"`（源文档为 Ms. Chen） |
| age / gender / occupation / ethnicity / patient_language | §3（patient_language 记录 `Chinese-only` 原文） |
| chief_complaint | §4 原文 |
| history_of_present_illness | §5 原文 |
| review_of_systems | §6 表格转 dict（system → relevant findings） |
| past_medical_history | §7 列表 |
| past_surgical_history / medications / allergies / family_history | §8 / §9 / §10 / §11 |
| personal_social_history | §12 各子项转 dict（Smoking/Alcohol/Diet/Physical Activity/Sleep/Occupational Stress/Travel/Support/Health Literacy） |
| sexual_history / obgyn_history | §13 / §14 |
| opening_statement | 依据 §2.1 首句翻译撰写，如 "我这四个星期胸口断断续续地疼，我担心是不是心脏出了问题。" |
| affect_style | 依据 §15 Psych 与 §2.1 翻译：`谈到心脏问题时略显焦虑；表达连贯；说中文` |
| ice | 依据 §5/§2.1：ideas=worried it is heart-related；concerns=father's recent MI；expectations=requests a full cardiac check-up |
| disclosure_rules | 编写（中文）：只按脚本回答；不讨论脚本之外的检查/结果；不给诊断 |
| qa_triggers | 编写 4-6 条中文触发（如 "吸烟"/"压力"/"运动"/"父亲" 及对应脚本回复），医学内容取自 §5/§12 翻译 |
| default_negative_response | `"这个我不太清楚，我没有这方面的信息。"` |
| examiner_pack.case_summary / working_diagnosis | §2.1 概括 / §17 |
| examiner_pack.differentials | §18 的 5 条 differentials |
| examiner_pack.structured_questions | §22 的 Q1–Q7 中文翻译（id=sq-1..sq-7，order=1..7，language=zh，reveal_items 见下） |
| examiner_pack.suggested_answers | §22 的 1a–7a Recommended Answer 中文翻译 |
| examiner_pack.physical_exam_release | §15 Physical Examination 按系统拆为 9 项（vital_signs/general/chest_wall/respiratory/cardiovascular/abdomen/extremities/neuro/psych），result 中文翻译 |
| examiner_pack.investigation_release | §16 拆为 4 项（cbc/chemistry/lipid_panel/ecg），result + reference_range 中文翻译 |
| examiner_pack.scoring_rubric | 自定（依据 §17–§20 与 7 道题）：max_score=100，criteria 按 7 道题各一条 + 汇报质量一条，字段 {id,label,description,weight}，label/description 中文 |
| review_record | review_status=`"approved"`，reviewer_name=`"Cecilia Xie"`，reviewed_at/published_at=2026-08-17（与 §1 Last updated 一致） |

`reveal_items` 语义：Q2（体格检查）→ physical_exam_release 各 item_id；Q3（辅助检查）→ investigation_release 各 item_id；其余题目 reveal_items=[]。（该字段供 feat-007 使用，本期只入库。）

- [ ] **Step 3: 校验文件可解析并导入**

```bash
cd /mnt/d/BRIDGE/backend && uv run python scripts/seed_cases.py
```
期望：`Imported 1 case(s): GP-ChestPain-0001`；再次运行输出相同（幂等）。

- [ ] **Step 4: 抽查导入内容与源文档一致**

用一段内联检查确认库中 7 道结构化问题与检查项数量：
```bash
cd /mnt/d/BRIDGE/backend && uv run python -c "
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Case
engine = create_engine('sqlite:///./bridge.db')
with Session(engine) as s:
    c = s.scalars(select(Case)).one()
    e = c.examiner_pack
    print('case:', c.id, 'status:', c.status.value)
    print('questions:', len(e.structured_questions))
    print('physical items:', len(e.physical_exam_release))
    print('investigation items:', len(e.investigation_release))
    print('rubric:', bool(e.scoring_rubric))
"
```
期望：case=GP-ChestPain-0001, status=published, questions=7, physical=9, investigation=4, rubric=True。

---

## Task 6: feat-010 T-010.5 导入测试

**Files:**
- Create: `backend/tests/test_seed_cases.py`

**Interfaces:**
- Consumes: `seed_cases(cases_dir, engine)`（Task 5）、`cases.schema.CaseFile`（Task 4）
- Produces: ≥5 个新增用例（含一条失败路径：非法文件被拒绝且不污染数据库）

- [ ] **Step 1: 新建 `backend/tests/test_seed_cases.py`**

```python
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Case
from scripts.seed_cases import seed_cases


@pytest.fixture()
def cases_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seed_test.db'}")
    yield engine
    engine.dispose()


def _write_case_file(cases_dir: Path, payload: dict, filename: str = "case.json") -> Path:
    path = cases_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _minimal_payload() -> dict:
    return {
        "case_id": "GP-ChestPain-0001",
        "title": "Stress-related chest pain",
        "type": "initial_visit",
        "system_tags": ["primary-care"],
        "difficulty": "medium",
        "language_availability": ["en"],
        "sections_language": {
            "student_instruction": "en",
            "history_taking": "en",
            "case_presentation": "en",
            "structured_questions": "en",
            "scoring": "en",
        },
        "learning_objectives": ["approach to chest pain"],
        "student_instructions": "Take a focused history.",
        "status": "published",
        "patient_information": {
            "name": "Ms. Chen",
            "age": 32,
            "gender": "female",
            "chief_complaint": "Recurrent chest pain.",
            "history_of_present_illness": "Intermittent pain.",
            "opening_statement": "I have chest pain.",
        },
        "examiner_pack": {
            "case_summary": "Chest pain.",
            "working_diagnosis": "Stress-related chest pain",
            "differentials": ["Angina"],
            "structured_questions": [
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "Diagnosis?",
                    "language": "en",
                    "reveal_items": [],
                }
            ],
            "suggested_answers": [{"question_id": "sq-1", "answer": "Stress-related."}],
            "physical_exam_release": [],
            "investigation_release": [],
            "scoring_rubric": {"max_score": 100, "criteria": []},
        },
    }


def test_seed_creates_published_case(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    imported = seed_cases(cases_dir, engine)
    assert imported == ["GP-ChestPain-0001"]
    with Session(engine) as s:
        case = s.scalars(select(Case)).one()
        assert case.status.value == "published"
        assert len(case.examiner_pack.structured_questions) == 1


def test_seed_is_idempotent(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    seed_cases(cases_dir, engine)
    seed_cases(cases_dir, engine)
    with Session(engine) as s:
        assert len(s.scalars(select(Case)).all()) == 1


def test_seed_imports_multiple_files(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload(), "a.json")
    second = _minimal_payload()
    second["case_id"] = "GP-HTN-0001"
    second["title"] = "Hypertension"
    _write_case_file(cases_dir, second, "b.json")
    imported = seed_cases(cases_dir, engine)
    assert sorted(imported) == ["GP-ChestPain-0001", "GP-HTN-0001"]


def test_invalid_file_rejected_without_db_pollution(cases_dir, engine):
    payload = _minimal_payload()
    del payload["title"]
    _write_case_file(cases_dir, payload, "bad.json")
    with pytest.raises(ValidationError):
        seed_cases(cases_dir, engine)
    with Session(engine) as s:
        assert s.scalars(select(Case)).all() == []


def test_reseed_reflects_file_changes(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    seed_cases(cases_dir, engine)
    updated = _minimal_payload()
    updated["title"] = "Updated title"
    _write_case_file(cases_dir, updated)
    seed_cases(cases_dir, engine)
    with Session(engine) as s:
        case = s.scalars(select(Case)).one()
        assert case.title == "Updated title"
```

- [ ] **Step 2: 运行全量测试并提交**

```bash
cd /mnt/d/BRIDGE && bash init.sh
```
期望：pytest 全绿（feat-010 相关新用例合计 ≥14 个）；typecheck/build 不受影响。

```bash
git add backend/cases backend/scripts/seed_cases.py backend/tests/test_seed_cases.py docs/case-file-format.md
git commit -m "feat(010): JSON case schema + seed workflow with Cecilia GP-ChestPain-0001 (idempotent)"
```

提交后更新 `feature_list.json`（feat-010 → completed，附证据：alembic 往返 OK、seed 输出、pytest 数量）。

---

## Task 7: feat-011 T-011.2 标准化病人对话模块

**Files:**
- Create: `backend/app/prompts/sp_system.txt`、`backend/app/prompts/sp_user.txt`
- Create: `backend/app/services/sp/__init__.py`、`backend/app/services/sp/patient.py`
- Test: `backend/tests/test_sp_patient.py`

**Interfaces:**
- Consumes: `app.services.llm.client.model_name()`（Task 1）
- Produces: `build_sp_messages(case_script: dict, history: list[dict], message: str, language: str) -> list[dict]`
- Produces: `SPResponder(client: AsyncOpenAI)`，方法 `async respond(case_script, history, message, language) -> str` 与 `async stream_response(case_script, history, message, language) -> AsyncIterator[str]`
- 约束：prompt 必须包含"只依据脚本回答""不编造检查结果""不给诊断/答案"

- [ ] **Step 1: 新建 `backend/app/prompts/sp_system.txt`**

```text
You are a Standardized Patient (SP) in a CCE practice station. Follow these rules strictly:
1. Answer only from the case script provided in the user message. Never add information that is not in the script.
2. Never fabricate physical examination or investigation results. If the script does not contain the answer, say you do not know or it was not provided.
3. Never give a diagnosis, differential diagnosis, management advice, or scoring hints. You are the patient, not the examiner.
4. Reply in {{LANGUAGE}}. Do not mix languages in one reply.
5. Stay in character and answer only what is asked, as a patient would in conversation.
```

- [ ] **Step 2: 新建 `backend/app/prompts/sp_user.txt`**

```text
Case script:
{{SCRIPT}}

History so far (student -> patient):
{{HISTORY}}

The student asks: {{MESSAGE}}
```

- [ ] **Step 3: 新建 `backend/app/services/sp/patient.py`**

```python
"""Standardized Patient dialogue module.

Builds chat messages from prompt templates and the case script, then calls
the LLM client. The SP must never go outside the case script (ADR-0002;
CONTEXT.md SP definition).
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from openai import AsyncOpenAI

from app.services.llm.client import model_name

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _render_script(case_script: dict) -> str:
    lines = []
    for key, value in case_script.items():
        if isinstance(value, (dict, list)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _render_history(history: list[dict]) -> str:
    if not history:
        return "(no questions asked yet)"
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)


def build_sp_messages(
    case_script: dict, history: list[dict], message: str, language: str
) -> list[dict]:
    system = load_prompt("sp_system.txt").replace("{{LANGUAGE}}", language)
    user = (
        load_prompt("sp_user.txt")
        .replace("{{SCRIPT}}", _render_script(case_script))
        .replace("{{HISTORY}}", _render_history(history))
        .replace("{{MESSAGE}}", message)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


class SPResponder:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def respond(
        self, case_script: dict, history: list[dict], message: str, language: str
    ) -> str:
        messages = build_sp_messages(case_script, history, message, language)
        resp = await self._client.chat.completions.create(
            model=model_name(), messages=messages
        )
        return resp.choices[0].message.content or ""

    async def stream_response(
        self, case_script: dict, history: list[dict], message: str, language: str
    ) -> AsyncIterator[str]:
        messages = build_sp_messages(case_script, history, message, language)
        stream = await self._client.chat.completions.create(
            model=model_name(), messages=messages, stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content
```

- [ ] **Step 4: 新建 `backend/tests/test_sp_patient.py`**

```python
import asyncio
from types import SimpleNamespace

from app.services.sp.patient import SPResponder, build_sp_messages


SCRIPT = {
    "name": "Ms. Chen",
    "age": 32,
    "chief_complaint": "Recurrent chest pain on and off for 4 weeks.",
    "opening_statement": "I have had chest pain on and off for 4 weeks.",
    "disclosure_rules": ["Answer only from script."],
}


class FakeCompletions:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))]
        )


class FakeClient:
    def __init__(self, reply: str = "I have had chest pain for 4 weeks.") -> None:
        self.completions = FakeCompletions(reply)

    @property
    def chat(self):
        return self


def test_build_sp_messages_include_script_and_constraints():
    messages = build_sp_messages(SCRIPT, [], "Do I have a heart attack?", "en")
    system, user = messages[0]["content"], messages[1]["content"]
    assert "Never fabricate" in system
    assert "case script" in system
    assert "Never give a diagnosis" in system
    assert "Recurrent chest pain on and off for 4 weeks." in user
    assert "Do I have a heart attack?" in user


def test_responder_calls_model_and_returns_reply():
    client = FakeClient(reply="I'm not sure. I just have this chest pain.")
    responder = SPResponder(client)  # type: ignore[arg-type]

    async def _run():
        return await responder.respond(SCRIPT, [], "What is wrong?", "en")

    reply = asyncio.run(_run())
    assert reply == "I'm not sure. I just have this chest pain."
    assert client.completions.kwargs["model"] == "deepseek-v4-flash"
    assert client.completions.kwargs["messages"][0]["role"] == "system"
```

- [ ] **Step 5: 运行测试**

```bash
cd /mnt/d/BRIDGE/backend && uv run pytest -q
```
期望：2 个新测试通过。

---

## Task 8: feat-011 T-011.3 评分模块

**Files:**
- Create: `backend/app/prompts/scoring_system.txt`、`backend/app/prompts/scoring_user.txt`
- Create: `backend/app/services/scoring/__init__.py`、`backend/app/services/scoring/schemas.py`、`backend/app/services/scoring/scorer.py`
- Test: `backend/tests/test_scoring.py`

**Interfaces:**
- Produces: `ScoreResult(score: int 0..100, feedback: str, reference_answer: str)`（Pydantic）
- Produces: `Scorer(client)`，`async score(case: dict, student_answers: list[dict], rubric: dict | None) -> ScoreResult`
- Produces: `NoRubricError(RuntimeError)`、`InvalidScoreOutputError(RuntimeError)`

- [ ] **Step 1: 新建 `backend/app/prompts/scoring_system.txt`**

```text
You are a clinical examiner scoring a medical student's CCE practice attempt.
Use ONLY the rubric and case materials provided in the user message.
Reply in JSON only, with exactly these keys:
{"score": <int between 0 and the rubric max_score>, "feedback": "<string>", "reference_answer": "<string>"}
Do not include any text outside the JSON object.
```

- [ ] **Step 2: 新建 `backend/app/prompts/scoring_user.txt`**

```text
Case summary: {{SUMMARY}}
Working diagnosis: {{WORKING_DIAGNOSIS}}
Structured questions and suggested answers:
{{QUESTIONS_AND_ANSWERS}}

Rubric:
{{RUBRIC}}

Student's answers:
{{STUDENT_ANSWERS}}

Provide the JSON score, feedback, and reference answer now.
```

- [ ] **Step 3: 新建 `backend/app/services/scoring/schemas.py` 与 `scorer.py`**

`schemas.py`：
```python
"""Output schema for AI scoring."""
from pydantic import BaseModel, Field


class ScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str
    reference_answer: str
```

`scorer.py`：
```python
"""AI scoring module — practice reference score from the rubric.

Refuses to score cases without a rubric (requirements section 9; CONTEXT.md
Rubric definition). Output is validated as ScoreResult.
"""
from __future__ import annotations

import json
from pathlib import Path

from openai import AsyncOpenAI

from app.services.llm.client import model_name
from app.services.scoring.schemas import ScoreResult

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


class NoRubricError(RuntimeError):
    """Raised when a case has no rubric and a score is requested."""


class InvalidScoreOutputError(RuntimeError):
    """Raised when the LLM output is not valid ScoreResult JSON."""


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def build_scoring_messages(
    case: dict, student_answers: list[dict], rubric: dict
) -> list[dict]:
    qa = "\n".join(
        f"Q{idx + 1}: {q.get('question', '')}\nSuggested: {a.get('answer', '')}"
        for idx, (q, a) in enumerate(
            zip(case.get("structured_questions", []), case.get("suggested_answers", []))
        )
    )
    answers = "\n".join(
        f"Q{item.get('question_id', idx + 1)}: {item.get('answer', '')}"
        for idx, item in enumerate(student_answers)
    )
    user = (
        load_prompt("scoring_user.txt")
        .replace("{{SUMMARY}}", case.get("case_summary", ""))
        .replace("{{WORKING_DIAGNOSIS}}", case.get("working_diagnosis", ""))
        .replace("{{QUESTIONS_AND_ANSWERS}}", qa)
        .replace("{{RUBRIC}}", json.dumps(rubric, ensure_ascii=False))
        .replace("{{STUDENT_ANSWERS}}", answers)
    )
    return [
        {"role": "system", "content": load_prompt("scoring_system.txt")},
        {"role": "user", "content": user},
    ]


class Scorer:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def score(
        self, case: dict, student_answers: list[dict], rubric: dict | None
    ) -> ScoreResult:
        if not rubric:
            raise NoRubricError("this case has no rubric; scoring refused")
        messages = build_scoring_messages(case, student_answers, rubric)
        resp = await self._client.chat.completions.create(
            model=model_name(), messages=messages, response_format={"type": "json_object"}
        )
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
            return ScoreResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidScoreOutputError(str(exc)) from exc
```

- [ ] **Step 4: 新建 `backend/tests/test_scoring.py`**

```python
import asyncio
from types import SimpleNamespace

import pytest

from app.services.scoring.scorer import (
    InvalidScoreOutputError,
    NoRubricError,
    Scorer,
)


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeClient:
    def __init__(self, content: str) -> None:
        self.completions = FakeCompletions(content)

    @property
    def chat(self):
        return self


def test_score_parses_valid_json():
    client = FakeClient(
        '{"score": 72, "feedback": "Good history", "reference_answer": "Stress-related chest pain."}'
    )
    scorer = Scorer(client)  # type: ignore[arg-type]
    result = asyncio.run(
        scorer.score(
            {"case_summary": "x", "working_diagnosis": "y",
             "structured_questions": [], "suggested_answers": []},
            [{"question_id": 1, "answer": "z"}],
            {"max_score": 100, "criteria": []},
        )
    )
    assert result.score == 72
    assert result.feedback == "Good history"
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}


def test_score_refuses_without_rubric():
    scorer = Scorer(FakeClient("{}"))  # type: ignore[arg-type]
    with pytest.raises(NoRubricError):
        asyncio.run(
            scorer.score(
                {"case_summary": "x"}, [{"question_id": 1, "answer": "z"}], None
            )
        )


def test_score_rejects_invalid_json():
    scorer = Scorer(FakeClient("not json"))  # type: ignore[arg-type]
    with pytest.raises(InvalidScoreOutputError):
        asyncio.run(
            scorer.score(
                {"case_summary": "x"},
                [{"question_id": 1, "answer": "z"}],
                {"max_score": 100, "criteria": []},
            )
        )
```

- [ ] **Step 5: 运行测试**

```bash
cd /mnt/d/BRIDGE/backend && uv run pytest -q
```
期望：3 个新测试通过。

---

## Task 9: feat-011 T-011.4 SSE 流式接口

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`（挂载 router）
- Test: `backend/tests/test_chat_stream.py`

**Interfaces:**
- Consumes: `SPResponder.stream_response(...)`（Task 7）、`app.services.llm.client.build_llm_client()`（Task 1）
- Produces: `POST /api/chat/stream`，请求体 `ChatStreamRequest{case_script, history, message, language}`，响应 `text/event-stream`，事件格式 `data: <chunk>\n\n`，结尾 `data: [DONE]\n\n`

- [ ] **Step 1: 新建 `backend/app/api/chat.py`**

```python
"""Streaming SP chat endpoint (SSE). Frontend integration lands in feat-005."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.llm.client import build_llm_client
from app.services.sp.patient import SPResponder

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    case_script: dict
    history: list[dict] = Field(default_factory=list)
    message: str
    language: str = "en"


def get_llm_client(request: Request):
    client = getattr(request.app.state, "llm_client", None)
    if client is None:
        request.app.state.llm_client = build_llm_client()
    return request.app.state.llm_client


@router.post("/stream")
async def chat_stream(request: Request, body: ChatStreamRequest) -> StreamingResponse:
    client = get_llm_client(request)
    responder = SPResponder(client)

    async def event_source():
        async for content in responder.stream_response(
            body.case_script, body.history, body.message, body.language
        ):
            yield f"data: {content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
```

`backend/app/main.py` 追加：
```python
from app.api import chat

app.include_router(chat.router, prefix="/api")
```

- [ ] **Step 2: 新建 `backend/tests/test_chat_stream.py`**

```python
from fastapi.testclient import TestClient

from app.main import app


class FakeStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for chunk in self._chunks:
                yield type(
                    "Chunk",
                    (),
                    {
                        "choices": [
                            type("Choice", (), {"delta": type("Delta", (), {"content": chunk})()})()
                        ]
                    },
                )()

        return gen()


class FakeCompletions:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream(self._chunks)


class FakeClient:
    def __init__(self, chunks: list[str]) -> None:
        self.completions = FakeCompletions(chunks)

    @property
    def chat(self):
        return self


def test_chat_stream_returns_sse_events():
    app.state.llm_client = FakeClient(["Hel", "lo", " there."])
    client = TestClient(app)
    response = client.post(
        "/api/chat/stream",
        json={
            "case_script": {"name": "Ms. Chen"},
            "history": [],
            "message": "Hi",
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert body.startswith("data: Hel")
    assert "data: [DONE]" in body
    assert app.state.llm_client.completions.kwargs["stream"] is True
```

- [ ] **Step 3: 运行测试并提交**

```bash
cd /mnt/d/BRIDGE && bash init.sh
```
期望：pytest 全绿；typecheck/build 不受影响。

```bash
git add backend/app/prompts backend/app/services/sp backend/app/services/scoring backend/app/api/chat.py backend/app/main.py backend/tests/test_sp_patient.py backend/tests/test_scoring.py backend/tests/test_chat_stream.py
git commit -m "feat(011): SP dialogue, AI scoring, SSE streaming endpoint"
```

提交后更新 `feature_list.json`（feat-011 → completed，附证据：smoke OK + 测试数量）。

---

## Task 10: 收尾 — 状态文档、全量验证、最终提交

**Files:**
- Modify: `docs/TASK-BREAKDOWN.md`（T-010.3 脱敏验收标准标记为 DEFERRED，注明用户决策与日期）
- Modify: `feature_list.json`（feat-010 / feat-011 completed + 证据）
- Modify: `progress.md`、`session-handoff.md`（本 session 完整记录；下一个 checkpoint commit）
- Modify: `docs/case-file-format.md`（如 Task 4 未含脱敏政策说明，则补）

- [ ] **Step 1: 更新文档**

`docs/TASK-BREAKDOWN.md` 的 T-010.3 验收标准第三条改为：
> **DEFERRED (2026-08-18):** ~~校验器明确拒绝可识别身份信息（规则来自 ADR-0002）~~ 用户决策：首期病例全为虚拟病例；加入真实病例前由用户亲自校验脱敏；ADR-0002 政策保留。

`feature_list.json`：feat-010 / feat-011 `status: "completed"`，evidence 写入实际命令输出（seed 导入结果、alembic 往返、smoke OK、pytest 通过数量）。

`progress.md`：新增本 session 段落（Session ID 009；Active Feature: feat-010 + feat-011；完成项、决策、文件、证据、风险：无 key 风险已解除；成本可见性仍待真实学生使用前补）。

`session-handoff.md`：Current Objective 更新为 feat-010/011 完成；Next step = feat-002 登录 或 feat-003 病例列表；阻塞清空。

- [ ] **Step 2: 全量验证**

```bash
cd /mnt/d/BRIDGE && bash init.sh
```
必须全绿：Secret hygiene check OK、后端 pytest 全绿、前端 typecheck 干净、build 成功。

- [ ] **Step 3: 确认 git 卫生并提交**

```bash
git status --short
git add docs progress.md feature_list.json session-handoff.md
git commit -m "docs(session): feat-010 + feat-011 completed — evidence, decisions, handoff"
git log --oneline -5
```
提交后 `git status --short` 必须为空；记录最终 checkpoint commit。

---

## Self-Review

**1. Spec coverage:**
* T-010.1 模型 → Task 2；T-010.2 迁移 → Task 3；T-010.3 schema+文档 → Task 4；T-010.4 种子+Cecilia → Task 5；T-010.5 测试 → Task 6。✓
* T-011.1 客户端+key → Task 1；T-011.2 SP → Task 7；T-011.3 评分 → Task 8；T-011.4 SSE → Task 9。✓
* 用户 2026-08-18 要求（key 先于 feat-010；脱敏暂缓；per-section 语言；thinking 默认开）→ 全部体现在 Global Constraints 与任务顺序。✓

**2. Placeholder scan:** 无 TBD/TODO；种子数据内容由 `Example teaching case.md` 逐段转写并有映射表，非占位。✓

**3. Type consistency:**
* `build_llm_client(http_client=None)` 在 Task 1 定义，Task 9 的 `get_llm_client` 使用（无参调用）✓
* `model_name()` 在 Task 1 定义，Task 7/8/9 使用 ✓
* `SPResponder.stream_response` 在 Task 7 定义，Task 9 使用 ✓
* `ScoreResult` 在 Task 8 定义并只在本模块使用 ✓
* `CaseFile`（Task 4）被 Task 5 种子脚本与 Task 6 测试使用，字段名一致（case_id/title/sections_language/...）✓
* `seed_cases(cases_dir, engine)`（Task 5）被 Task 6 测试按同签名调用 ✓
