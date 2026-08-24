# Session Progress Log

## Current State

**Last Updated:** 2026-08-24 (session)
**Session ID:** dsh-session (BRIDGE OSCE 分支整理)
**Active Feature:** feat-008 — 仓库 Harness 脚手架（五件套）

## Status

### What's Done

- [x] 确认本地 `260824-OSCE` 与 `origin/260824-OSCE` 完全同步（`ba7f7db`，0 ahead/0 behind）
- [x] 遍历并报告 OSCE 分支架构与技术栈（Nuxt 4 + Pinia + Tailwind / Flask + SQLite + JWT + OpenAI 兼容大模型）
- [x] 配置 DeepSeek V4 Flash（方法 B：后端环境变量 `OPENAI_API_KEY/BASE_URL/MODEL`），实测 AI 走真实模型
- [x] 把 `Example teaching case.md`（压力/焦虑相关胸痛）整理并入库为 **GP-003**（全科，病人中文/考官英文、语言不符提醒）
- [x] 工作区整并：`/mnt/d/BRIDGE` 切到 `260824-OSCE`，删除临时 worktree `/mnt/d/BRIDGE-osce`（含其 pnpm fix 提交 `a838438`）
- [x] 修复前端构建坑：清除旧项目残留 `node_modules/tailwindcss@4`，重装后正确解析 v3.4.19，`pnpm build` 通过
- [x] `.agents/` 本地化：从 feat 分支复制回工作区 + 加入 `.gitignore`（OSCE 分支提交 `3404449`）
- [x] 将 `.agents/` 从 GitHub `master` 移除并 push（`f5c0385`），master `.gitignore` 已加 `.agents/`
- [x] 清理所有未跟踪杂物（`.codex-investigation/`、`harness-repo/`、`OSCE开发(1).md`、`backend/bridge.db`）
- [x] 删除 `feat/010-011-case-llm` 分支（本地+远端），备份 tag `archive/feat-010-011`（= `5b71a80`，含 feat-010/011 代码 + 中文版 Cecilia 病例）已推送 GitHub
- [x] 修复病例库：补回缺失的 OG-002，病例库恢复为 **13 例**（12 内置 + GP-003）

### What's In Progress

- [ ] feat-008：创建 harness-creator 五件套（AGENTS.md / feature_list.json / progress.md / session-handoff.md / init.sh）
  - 待验证：`./init.sh` 跑通

### What's Next

1. 运行 `./init.sh` 验证五件套基线（后端依赖 + 前端构建）
2. 将五件套提交到 `260824-OSCE` 分支
3. 确认后端(:5000)/前端(:3000) 服务正常，网站 http://localhost:3000 可访问

## Blockers / Risks

- [x] 已解决：前端 Tailwind v4/v3 冲突（残留 `node_modules/tailwindcss@4`）
- [x] 已解决：病例库丢失 OG-002（已从 `seed_data.py` 补回）
- [ ] 风险：`JWT_SECRET` 仍用默认 `dev-secret-*`，生产需更换
- [ ] 风险：CORS 当前允许所有来源（`origins: *`），上线前需收紧
- [ ] 风险：DeepSeek key 通过环境变量注入，未落盘；重启后端需重新注入环境变量

## Decisions Made

- **工作区以 `/mnt/d/BRIDGE` 为准**：切到 `260824-OSCE` 分支，删除临时 worktree
  - Context：主仓库 `BRIDGE` 才是仓库本体，worktree 只是临时隔离
- **`.agents/` 不进版本库**：复制回本地 + gitignore，作为本地独有 agent 配置/技能
  - Context：`.agents` 属本地/开发配置，不应被 git 跟踪；master 与 OSCE 分支均已处理
- **病例 prompt 语言**：病人说中文、考官说英文（并在 prompt 中硬性规定 + 语言不符提醒）
  - Context：用户指定；对应前身 repo 的 SP/Viva 双语模型
- **DeepSeek 用方法 B（环境变量）**：短期开发使用；数据库 `llm_configs` 表为空，后台 LLM 配置优先于环境变量

## Files Modified This Session

- `.gitignore` — 加入 `.agents/`（OSCE 分支 `3404449`）
- `backend/osce.db` — 病例库（13 例，含 GP-003）
- `AGENTS.md`, `feature_list.json`, `progress.md`, `session-handoff.md`, `init.sh` — harness-creator 五件套（新建）
- (feat 分支 `5b71a80`、master `f5c0385` 各含前述提交)

## Evidence of Completion

- [x] 后端 `http://127.0.0.1:5000/api/health` → `{"status":"ok"}`
- [x] 前端 `http://127.0.0.1:3000/` → HTTP 200
- [x] `/api/cases` 返回 13 例（OG-002、GP-003 均在）
- [x] 实测：病人中文开场、考官英文提问、考生用中文时考官提醒"Please answer in English"
- [x] admin/admin123 登录正常；`deploytest01/test123456` 学生登录正常
- [ ] 待跑：`./init.sh` 基线验证

## Notes for Next Session

- 服务当前在跑：后端 `127.0.0.1:5000`、前端 `127.0.0.1:3000`（DeepSeek 注入）。
- 重启后端的标准命令见 `start-backend.bat`（Windows）或手工注入环境变量（WSL）。
- 若管理员想在后台持久配置模型：用 admin 登录 → /admin → 大模型管理（DB 配置优先于环境变量）。
- 待办建议：换掉默认 JWT_SECRET、收紧 CORS、正式化 DeepSeek 配置。
