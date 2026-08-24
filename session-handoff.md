# Session Handoff

## Current Objective

- **Goal:** 把 BRIDGE 仓库整理到以 OSCE 网站分支为工作区，污染/废弃内容清理完毕，建立 harness-creator 规范的可交接仓库。
- **Current status:** OSCE 分支 `260824-OSCE` 为当前工作分支，工作区干净（`git status` 空），服务在跑，病例库 13 例，harness 五件套已创建（待 `./init.sh` 验证后提交）。
- **Branch / commit:** `260824-OSCE` @ `3404449`（`.agents` gitignore 提交）

## Work Completed This Session

- [x] 确认 `260824-OSCE` 分支与远端同步
- [x] 遍历并报告 OSCE 分支架构/技术栈
- [x] 接入 DeepSeek V4 Flash（环境变量），AI 走真实模型
- [x] 用 `Example teaching case.md` 新增病例 **GP-003**（全科，压力/焦虑相关胸痛；病人中文、考官英文+语言提醒）
- [x] 工作区整并：`/mnt/d/BRIDGE` 切到 `260824-OSCE`，删除临时 worktree `/mnt/d/BRIDGE-osce`
- [x] 修复前端 Tailwind v4/v3 构建冲突（清残留后重装，`pnpm build` 通过）
- [x] `.agents/` 本地化并 gitignore（OSCE 分支 `3404449`；master `f5c0385` 已推送）
- [x] 清理全部未跟踪杂物；删除 `feat/010-011-case-llm` 分支（备份 tag `archive/feat-010-011`）
- [x] 修复病例库（补回 OG-002，库=13 例）
- [x] 创建 harness-creator 五件套：`AGENTS.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`init.sh`

## Verification Evidence

| Check | Command | Result | Notes |
|---|---|---|---|
| 后端健康 | `curl :5000/api/health` | `{"status":"ok"}` | 服务在跑 |
| 前端 | `curl :3000/` | HTTP 200 | 生产构建服务 |
| 病例库 | `curl :5000/api/cases?pageSize=50` | total=13 | 含 OG-002、GP-003 |
| 前端构建 | `cd frontend && pnpm build` | exit 0 | Tailwind v3.4.19 正确解析 |
| 后端依赖 | `cd backend && .venv/bin/python -c "import app"` | ok | Flask 3.1.1 |
| 登录 | admin/admin123、deploytest01/test123456 | ok | |

## Files Changed

- `AGENTS.md` — harness 指令文件（OSCE 项目版，新建）
- `feature_list.json` — 功能状态表（新建）
- `progress.md` — 会话日志（新建）
- `session-handoff.md` — 本交接文档（新建）
- `init.sh` — 启动/验证脚本（新建，待验证）
- `backend/osce.db` — 病例库（13 例，含 GP-003、OG-002）
- `.gitignore` — 加入 `.agents/`（已提交 `3404449`）

## Decisions Made

- 工作区以 `/mnt/d/BRIDGE` + `260824-OSCE` 分支为准，删除临时 worktree。
- `.agents/` 作为本地独有配置，不进版本库（OSCE 与 master 均已 gitignore，master 已推 GitHub）。
- 病例 prompt：病人中文、考官英文（硬性 + 语言不符提醒）。
- DeepSeek 用环境变量（方法 B）；DB `llm_configs` 为空，后台配置优先于环境变量。

## Blockers / Risks

- `JWT_SECRET` 仍为 `dev-secret-*`，生产需更换。
- CORS `origins: *`，上线前需收紧。
- DeepSeek key 靠环境变量注入、未落盘；重启后端需重新注入。

## Next Session Startup

1. Read `AGENTS.md`.
2. Read `feature_list.json` and `progress.md`.
3. Review this handoff.
4. Run `./init.sh`（或文档中的验证命令）before editing.

## Recommended Next Step

- 运行 `./init.sh` 验证五件套基线，通过后把五件套提交到 `260824-OSCE` 分支。
- 随后可选：更换默认 `JWT_SECRET`、收紧 CORS、把 DeepSeek 配置正式化（环境变量或后台），或继续拓展教学病例库。
