# Session Handoff

## Current Objective

- Goal: 首期 CCE 练习系统（2–4 周 MVP，一个月内给老师演示）
- Current status: **feat-010 + feat-011 完成**（病例数据模型/种子工作流 + DeepSeek V4 Flash 适配，全部验证通过）；下一活动 feature = **feat-002 学生/教师登录**（随后 feat-003 病例列表）
- Branch / commit: `feat/010-011-case-llm` @ 干净 checkpoint（见 `git log --oneline -1`）

## Completed This Session

- [x] feat-011 DeepSeek V4 Flash 适配：LLM client + key 卫生 + 真实 smoke OK（`0c0743a`）；SP 对话（`890235b`）、AI 评分（`0918da5`）、SSE 流式端点（`af29f26`）
- [x] feat-010 病例数据模型与种子工作流：领域模型（`4d08a02`）、Alembic 迁移（`2fe7485`）、JSON schema + `docs/case-file-format.md`（`19ba1a4`）、中文 Cecilia GP-ChestPain-0001 幂等种子（`d313764`）、导入测试（`7ca5659`）
- [x] 首期演示中文版：Cecilia 病例 `sections_language` 全 `zh`，内容按 `Example teaching case.md` 中文翻译（医学事实不变）
- [x] 脱敏政策记录：本期虚拟病例不做自动脱敏校验（用户 2026-08-18 决策；ADR-0002 保留；TASK-BREAKDOWN T-010.3 标注 DEFERRED）
- [x] 子代理不稳定根因调研（MultiAgentV2 `encrypted_content` 对第三方 provider 不可见）写入 `docs/research/2026-08-18-codex-subagent-instability.md`；config 已加 `multi_agent_v2 = false`

## Verification Evidence

| Check | Command | Result | Notes |
|---|---|---|---|
| 后端测试 | `uv run pytest -q`（WSL） | 22 passed | health/LLM/models/schema/seed/SP/scoring/SSE |
| 种子导入 | `uv run python scripts/seed_cases.py` ×2 | idempotent | GP-ChestPain-0001：7 题 / 9 体格 / 4 检查 / rubric / published |
| 数据库迁移 | `uv run alembic upgrade head` + `downgrade base` | OK | 往返无损 |
| 真实 LLM smoke | `uv run python scripts/smoke_llm.py` | SMOKE OK | key 来自 git-ignored `backend/.env` |
| 前端类型 | `npm run typecheck` | clean | tsc -b |
| 前端构建 | `npm run build` | OK | 218.37 kB JS / 7.98 kB CSS |
| 密钥卫生 | `bash init.sh` secret hygiene | OK | `backend/.env` git-ignored 且未被跟踪 |
| Git 干净 | `git status --short` | empty | 最新 checkpoint |

## Files Changed

- `backend/cases/`（schema + GP-ChestPain-0001.json）、`backend/scripts/seed_cases.py`、`backend/app/services/{llm,sp,scoring}/`、`backend/app/prompts/`、`backend/app/api/chat.py`、`backend/app/main.py`
- `backend/tests/`（test_llm_client / test_models / test_case_schema / test_seed_cases / test_sp_patient / test_scoring / test_chat_stream）
- `docs/case-file-format.md`、`docs/TASK-BREAKDOWN.md`、`docs/research/2026-08-18-codex-subagent-instability.md`、`feature_list.json`、`progress.md`、`session-handoff.md`

## Decisions Made

- 首期演示中文版病例（2026-08-18）：Cecilia `sections_language` 全 `zh`；平台 UI 仍英文（ADR-0001）
- 脱敏：本期虚拟病例不自动校验，真实病例由用户亲自校验（ADR-0002，T-010.3 DEFERRED）
- API key：只在本机 `backend/.env` / `~/.codex/config.toml`；不上 GitHub、不用中转站
- 子代理：当前 session 锁定 MultiAgentV2 无法投递任务 → 控制器内联执行；下次冷启动新 session + `multi_agent_v2 = false` 后再启用子代理
- 主力模型组合：Codex CLI + deepseek-v4-flash-0731（V1），不订阅双套餐；啃不动的任务走人工回退

## Blockers / Risks

- [ ] 子代理投递需冷启动验证：`multi_agent_v2 = false` 已写入 config，但需新 session 验证 v1 workaround
- [ ] API 成本无上限：正式给学生使用前必须补用量统计
- [ ] WSL 通过 `/mnt/d` 访问仓库 IO 略慢（已接受）；uv 硬链接跨文件系统告警（已自动回退 copy）

## Next Session Startup

1. 按 `docs/STARTUP-CHECKLIST.md` 逐项执行（读上下文 → 验证 checkpoint → 选任务）
2. 本会话后最新 checkpoint 见 `git log --oneline -1`
3. 运行 `bash init.sh`（WSL）确认全绿

## Recommended Next Step

- 开始 **feat-002 学生/教师登录**（T-002.1~T-002.4，验收标准见 `docs/TASK-BREAKDOWN.md`）
- 之后 **feat-003 病例列表** → **feat-004 CCE 站流程壳**，逐步打通 M1 演示链路
