# Session Progress Log

## Current State

**Last Updated:** 2026-08-25 (session)
**Session ID:** dsh-session (病例字段精简 + 统一 Prompt 骨架)
**Active Feature:** 移除病例库 `difficulty` 字段；取消每个病例独立的 patient_prompt/examiner_prompt，改为统一的 patient/考官/评估 prompt 骨架函数（feat-011）

## Status

### This Session — 病例字段精简 + 统一 Prompt 骨架（最小改动）

- [x] **移除病例库 `difficulty` 字段**（后端 schema + API + 前端展示）：
  - `backend/schema.sql` `cases` 表去掉 `difficulty` 列；
  - `backend/seed_data.py` 去掉全部 12 例的 `difficulty`；
  - `backend/cases.py` `case_to_dict`/`case_detail_to_dict` 去掉 `difficulty`；
  - `backend/admin.py` 校验/CRUD/导入/CSV 模板去掉 `difficulty`；
  - 前端 `types/index.ts`（CaseSummary 去 `difficulty`）、`CaseBox.vue`（去难度徽标）、`CaseManager.vue`（去「难度」列）、`CaseForm.vue`（去难度下拉）、`CsvUploader.vue`（CSV 模板去难度列）。
  - 对已存在的 `backend/osce.db` 做就地列迁移（`database._migrate_cases`，幂等 `ALTER TABLE ... DROP COLUMN`），保留 13 例既有病例与既有会话。
- [x] **取消每个病例独立的 `patient_prompt`/`examiner_prompt`**，改为统一 prompt 骨架函数（`backend/prompts.py`）：
  - 新增 `patient_system_prompt(case)` / `examiner_system_prompt(case)` / `assessment_system_prompt(case, transcript)`，接口极小（case -> str 或 case+transcript -> str），把模板构造/插值/规则全部封装（深度抽象）。
  - `backend/ai_service.py`：`patient_reply`/`examiner_reply` 改用 `prompts.*`；`grade_session` 改为先 `_build_transcript(content)` 扁平化对话，再内联进 `assessment_system_prompt`，并发送固定 user 消息（对齐 reference 文档 §4.2）。
  - `backend/sessions.py`：`_get_owned_session`/`_grade_and_save` 查询去掉 prompt 列、补 `c.case_no`；`_case_payload` 改为返回 title/department/summary/reference_answer/case_id/case_no。
  - `backend/admin.py`、`backend/cases.py`、`backend/database.py`：去掉 patient/examiner prompt 相关写入与字段。
  - 前端 `CaseForm.vue` 去掉「AI 病人提示词/考官提示词」输入框；`CsvUploader.vue` CSV 模板去掉这两列；`types/index.ts` `CaseDetail` 去掉 `patientPrompt`/`examinerPrompt`。
  - 语言规则：SP 说中文、考官说英文，本次不做中英文切换（在骨架中硬性规定）。
- [x] `bash init.sh` 基线通过（backend import + db 迁移/init + nuxt prepare）。
- [x] `cd frontend && pnpm build` 全量生产构建通过（exit 0，2.49 MB / 636 kB gzip）。
- [x] 冒烟 e2e：`cd frontend && bash e2e.sh` 2/2 通过（病例列表 + admin 登录）。
- [x] **独立 evaluator 子代理端到端验证通过（PASS）**：`cd frontend && bash e2e.sh` 5/5 通过（官方病例全流程 + admin 管理 + 导入新病例并删除 + 冒烟 2 项）；`cases` 表列已确认为 `case_id/case_no/title/department/summary/reference_answer/is_active/created_at/updated_at`（无 `difficulty`/`patient_prompt`/`examiner_prompt`），病例 13 例；前端无难度徽标/「难度」列/难度下拉/AI病人-考官提示词输入框；`prompts.patient_system_prompt`（中文含摘要）、`examiner_system_prompt`（英文含参考答案）、`assessment_system_prompt`（要求 JSON、内联对话）均实测通过；导入用例 `EVAL-1787634428200` 已删除（DB count=0，总病例回到 13）；临时 spec/CSV 已清理，`frontend/e2e/` 仅剩 `smoke.spec.ts`；全程无未捕获页面错误。

### This Session — 移除倒计时功能（最小改动）

- [x] 移除前端 `frontend/app/pages/session/[sessionid].vue` 的倒计时能力：删除「剩余时间」UI、`secondsLeft`/`timeUp`/`timer` 状态、`timerText`/`timerClass`、`startTimer`/`stopTimer`、`onMounted` 的计时启动、`watch(timeUp)` 的到时自动提交/提示，以及 `onBeforeUnmount(stopTimer)`；把 `timeUp` 从 `:disabled` 绑定中剔除。
- [x] 移除后端 `backend/sessions.py` 的时限逻辑：删除 `SESSION_SECONDS`、`_deadline_expired()`、`now + timedelta(...)` 的 deadline 计算，及 `send_message`/`end_inquiry` 两处把状态置为 `expired` 并返回 `408 会话已超过8分钟` 的拦截。保留 `deadline_at` 列（schema 为 NOT NULL，改为写入创建时间，避免变更数据库/迁移），未再被任何逻辑使用。
- [x] 更新文档：`feature_list.json`（feat-003 描述去掉「8 分钟倒计时」）、`README.md`（`/session/{sessionid}` 描述去掉倒计时）。
- [x] `bash init.sh` 基线通过（backend import + db init + nuxt prepare）。
- [x] `cd frontend && pnpm build` 全量生产构建通过（exit 0）。
- [x] **独立 evaluator 子代理端到端验证通过（PASS）**：`cd frontend && bash e2e.sh` 冒烟 2/2 通过（病例列表 + admin 登录）；临时会话流用例通过——注册新学生 → 首页选病例开始练习 → 会话页确认倒计时已移除（无「剩余时间」、无 `MM:SS`、无计时/到时控件）→ AI 病人问询回复 → 结束问询（AI 考官阶段）→ 提交审查 → `/report` 展示 ScoreBox/AnswerBox；全程无「时间已到/超过8分钟/会话已超过8分钟」告警、无未捕获页面错误；临时用例与测试数据已清理，仓库只含本次改动。验证细节见「端到端验证门禁」。
- [x] 说明：保留 `deadline_at` 列（schema NOT NULL，改为写入创建时间），未改动数据库/迁移；`expired` 状态/展示逻辑保留（兼容历史数据），仅当历史数据存在时才会出现。

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

### This Session (feat-009) — 依赖本地化与 gitignore 硬化

- [x] 确认当前分支 `260824-OSCE` 与工作区干净（无依赖产物被 git 跟踪）
- [x] 确认后端 pip 依赖隔离在 `backend/.venv`（`.venv/bin/python`，含自建 `.gitignore`）
- [x] 确认前端 npm/pnpm 依赖隔离在 `frontend/node_modules`（`.pnpm` store，690 包）
- [x] 硬化 `.gitignore`：新增 `.pytest_cache/.ruff_cache/.mypy_cache/__pycache__/*.egg-info/.coverage`、泛化 `.venv/`、补 `.output/.nuxt/.data/.nitro`、日志/构建产物等；并保留 lockfile（pnpm-lock.yaml）、manifests、configs 仍可跟踪
- [x] `git check-ignore` 覆盖全部依赖/缓存目录（node_modules/.nuxt/.output/dist/.venv/.pytest_cache/__pycache__）；合法文件 package.json/pnpm-lock.yaml/requirements.txt/.env.example 等未被误忽略
- [x] `bash init.sh` 通过（后端 deps/import/db + 前端 nuxt prepare）
- [x] `cd frontend && pnpm build` 全量生产构建通过（2.49 MB / 637 kB gzip）

### This Session (feat-010) — Playwright 端到端验证门禁

- [x] 本地安装 `@playwright/test@1.62.1`（frontend devDependency，落在 frontend/node_modules）
- [x] 安装 Chromium 浏览器于 `~/.cache/ms-playwright`（完整版，`channel: 'chromium'`；headless-shell 未装，用全量 Chromium 跑无头可正常工作）
- [x] 新增 `frontend/playwright.config.ts`（自动拉起后端:5000 + 前端:3000，已运行则复用；直接调 bin 避开 pnpm 只读 store）
- [x] 新增 `frontend/e2e/smoke.spec.ts`（病例列表渲染 + admin 登录，覆盖完整流程）
- [x] 新增 `frontend/e2e.sh` 包装脚本（绕过环境 HTTP 代理对 localhost 干扰；直接 exec playwright，免 pnpm store）
- [x] 新增 `frontend/package.json` e2e script = `bash e2e.sh`；`.gitignore` 加 Playwright 产物（test-results/ playwright-report/ blob-report/ *.last-run.json）
- [x] `bash e2e.sh` 冒烟通过 2/2（首页病例列表 + admin 登录 OPTIONS/POST 200）
- [x] AGENTS.md 加入「端到端验证门禁（Evaluator Gate）」：任何改动/交接前必须由独立上下文的 evaluator 子代理运行 `cd frontend && bash e2e.sh` 并全部通过；并把该门禁纳入 DoD

### What's In Progress

- 无（当前会话工作已完成）

### What's Next

1. **当前无未完成 feature**：`feature_list.json` 10 项全 done；本会话移除 8 分钟倒计时已提交（`717923e`）。
2. 推荐下一步：生产化加固——更换默认 `JWT_SECRET`、收紧 CORS `origins:*`、把 DeepSeek 配置正式化（环境变量或经 `/admin` 后台持久化）。
3. 或扩充 e2e 用例：注册/登录、会话流、个人中心等长流程，并固化进 `frontend/e2e/` 供后续 evaluator 门禁复用。
4. 任一改动交接前，按 AGENTS.md 门禁用独立 evaluator 子代理跑 `cd frontend && bash e2e.sh` 并全部通过。

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

- (本会话 移除倒计时)
  - `backend/sessions.py` — 移除 `SESSION_SECONDS`/`_deadline_expired`/时限拦截
  - `frontend/app/pages/session/[sessionid].vue` — 移除倒计时 UI/逻辑
  - `README.md`、`feature_list.json`、`progress.md`、`session-handoff.md` — 文档/工件更新
  - 提交 `717923e`：`feat(session): remove 8-minute countdown / time-limit feature`（5 files, +20/−92）
- (上一会话 feat-009)`.gitignore`、`feature_list.json`、`progress.md`
- (本会话 feat-010)
  - `frontend/package.json` — 加 `@playwright/test` devDependency + `e2e` script
  - `frontend/pnpm-lock.yaml` — lockfile 更新（@playwright/test）
  - `frontend/playwright.config.ts`、`frontend/e2e/smoke.spec.ts`、`frontend/e2e.sh` — 新增
  - `.gitignore` — 加 Playwright 产物忽略
  - `AGENTS.md` — 加「端到端验证门禁（Evaluator Gate）」并纳入 DoD
  - `feature_list.json`、`progress.md` — 状态更新

## Evidence of Completion

- [x] 后端 `http://127.0.0.1:5000/api/health` → `{"status":"ok"}`
- [x] 前端 `http://127.0.0.1:3000/` → HTTP 200
- [x] `/api/cases` 返回 13 例（OG-002、GP-003 均在）
- [x] 实测：病人中文开场、考官英文提问、考生用中文时考官提醒"Please answer in English"
- [x] admin/admin123 登录正常；`deploytest01/test123456` 学生登录正常
- [x] `./init.sh` 基线验证通过（backend import + db init + nuxt prepare）
- [x] 独立 evaluator e2e PASS：`cd frontend && bash e2e.sh` 冒烟 2/2 + 会话流用例 1/1（倒计时已移除、全流程可用、无超时告警）

## Notes for Next Session

- 本会话已移除问诊会话的 8 分钟倒计时/时限（提交 `717923e`），独立 evaluator e2e PASS，仓库干净。
- 服务不一定在跑：可用 `cd frontend && bash e2e.sh`（Playwright `webServer` 会自动拉起后端 `:5000` 与前端 `:3000`，已运行则复用）。
- 重启后端的标准命令见 `start-backend.bat`（Windows）或手工注入环境变量（WSL）；未配置 `OPENAI_API_KEY` 时 AI 走内置 Mock（e2e 稳定）。
- 若管理员想在后台持久配置模型：用 admin 登录 → /admin → 大模型管理（DB 配置优先于环境变量）。
- 待办建议：换掉默认 JWT_SECRET、收紧 CORS、正式化 DeepSeek 配置。
