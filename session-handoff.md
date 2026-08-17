# Session Handoff

## Current Objective

- Goal: 首期 CCE 练习系统（2–4 周 MVP，一个月内给老师演示）
- Current status: **feat-001 完成**（技术栈与骨架锁定并验证）；下一活动 feature = **feat-010 病例数据模型与种子工作流**
- Branch / commit: `master` @ `f6e7ff2`（干净 checkpoint；本会话后续文档提交为下一个 commit）

## Completed This Session

- [x] Grill-with-docs 拷问完成（Rounds 1–2），用户确认共识：FastAPI + React + shadcn/ui；SQLite dev → Postgres prod；英文界面；真人病例脱敏；二期功能只记录不实现
- [x] ADR 0001–0004 写入 `docs/adr/`
- [x] WSL 开发环境：安装 node 24.19 / npm 11.17 / uv 0.12.5（python 3.14.4 已有）
- [x] 后端骨架（FastAPI + health API + pytest 1 passed）、前端骨架（Vite 8 + React 19 + TS 6 + Tailwind v4 + shadcn 配置）
- [x] `init.sh` 真实验证通过（后端 pytest / 前端 typecheck / build）
- [x] 启动就绪清单 `docs/STARTUP-CHECKLIST.md`、任务分解 `docs/TASK-BREAKDOWN.md`

## Verification Evidence

| Check | Command | Result | Notes |
|---|---|---|---|
| 后端测试 | `uv run pytest -q`（WSL） | 1 passed | health endpoint |
| 前端类型 | `npm run typecheck` | clean | tsc -b |
| 前端构建 | `npm run build` | OK | 218.37 kB JS / 7.98 kB CSS |
| Harness 结构 | `validate-harness.mjs` | 100/100 | 五子系统全 5/5 |
| Git 干净 | `git status --short` | empty | checkpoint `f6e7ff2` |

## Files Changed

- `backend/`（FastAPI 骨架）、`frontend/`（Vite+React+TS 骨架）、`scripts/setup-dev.sh`、`init.sh`
- `docs/adr/0001..0004`、`docs/STARTUP-CHECKLIST.md`、`docs/TASK-BREAKDOWN.md`、`docs/tech-stack-{questions,research}.md`
- `CONTEXT.md`、`AGENTS.md`、`feature_list.json`、`progress.md`、`README.md`

## Decisions Made

- 技术栈/数据库/UI/隐私/二期边界：见 `docs/adr/0001–0004`
- 开发环境：命令统一在 WSL（Ubuntu 2）跑，仓库在 `/mnt/d/BRIDGE`
- 演示范围：登录 → 学生端跑通 1 个病例 → 教师端基础统计（M1 里程碑，见 `docs/TASK-BREAKDOWN.md`）

## Blockers / Risks

- [ ] `DEEPSEEK_API_KEY` 未注册：feat-011/005/008 联调必须用 mock，不得假装联调
- [ ] WSL 通过 `/mnt/d` 访问仓库 IO 略慢（已接受）；uv 硬链接跨文件系统告警（已自动回退 copy）
- [ ] API 成本无上限：正式给学生使用前必须补用量统计

## Next Session Startup

1. 按 `docs/STARTUP-CHECKLIST.md` 逐项执行（读上下文 → 验证 checkpoint → 选任务）
2. 本会话后最新 checkpoint 见 `git log --oneline -1`
3. 运行 `bash init.sh`（WSL）确认全绿

## Recommended Next Step

- 开始 **feat-010**：先做 **T-010.1 领域数据模型**（验收标准见 `docs/TASK-BREAKDOWN.md`）
