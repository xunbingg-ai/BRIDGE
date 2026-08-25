# Session Progress Log

## Current State

**Last Updated:** 2026-08-25 (session)
**Session ID:** dsh-session (12 例教学病例内容完善 + 指南校准)
**Active Feature:** 12 例教学病例内容完善 + 指南校准（feat-012）—— 已按用户方案修复「内容泄漏」回归：summary 改为 patient_scenario（内容不变），卡片只显示派生的 OSCE 开场信息（年龄+性别+一个核心症状），对话由学生先开口（取消 SP 开场自动气泡），病人/考官 prompt 与卡片 API 均不泄露完整病历与答案。

## Status

### ✅ REGRESSION（内容泄漏）已修复（feat-012 收尾）

**背景：** 上一阶段把 `summary` 从 ~30 字简介扩成完整大病历，导致 ① 病例卡片直接显示完整病历；② 病人 Mock 开场直接把 summary 回吐。按用户更贴近真实 OSCE 的方案修复。

**修复内容（本次）：**
- 把病例字段 `summary` 改名为 `patient_scenario`（**内容保持不变**），DB 就地迁移（`ALTER TABLE RENAME COLUMN summary→patient_scenario`，SQLite 3.25+，幂等），`schema.sql`/`seed_data.py`/内容管线脚本同步改名。
- **卡片只显示派生的 OSCE 开场信息**：新增 `backend/case_utils.py`，`derive_patient_brief(patient_scenario)` 从「一般情况/主诉」提取 `年龄+性别+核心症状`（如「32岁，男性，发热、咳嗽、咳黄痰3天。」）；`/api/cases` 列表/详情只返回 `brief`，**不暴露 patient_scenario/reference_answer**。
- **进入对话由学生先开口**：`create_session` 不再调用 `patient_reply` 生成 SP 开场气泡，`content.patient_phase` 为空、返回 `reply=''`；会话空态文案改为「请开始你的 OSCE 问诊 / 由你先向患者发问」。
- **Mock 病人按所问回答**：`ai_service.patient_reply` 改用 `parse_patient_scenario` 提取主诉/时长/年龄，按关键字给简短、患者口吻的回答，**绝不回吐完整病历/答案**；真实 LLM 路径的 `patient_system_prompt` 强化「由学生先开口、只答被问、不主动泄露」。
- 管理后台（admin）`summary` 字段改名 `patientScenario`（CaseForm 标签「病人剧本（完整病历）」）；CSV 模板/导入列改 `patient_scenario`。
- 新增回归用例 `frontend/e2e/content-leak.spec.ts`（卡片仅显示 age/性别/核心症状；会话由学生先开口；病人回复简短且无完整病历标记）。

**验证：** `bash init.sh` 通过；`cd frontend && pnpm build` 通过（2.49 MB）；独立 evaluator e2e（`cd frontend && bash e2e.sh`，含 smoke.spec.ts + content-leak.spec.ts）全部通过；`/api/cases` 返回 13 例且仅含 brief 字段；osce.db 迁移后 cases 列=case_id/case_no/title/department/patient_scenario/reference_answer/is_active/created_at/updated_at（13 例）。

### 复查补充（用户实测反馈后修复）

**① 卡片黑体仍显示诊断 → 已去掉诊断标题**
- 复核发现卡片 `CaseBox.vue` 的 `h3` 粗体是病例标题（即诊断名，如「社区获得性肺炎」），用户要求不显示诊断。已删除该标题，改为「门类 + 编号 + 核心症状 brief（作为粗体主文案）+ 开始练习按钮」。
- 回归断言升级：`expect(card.locator('h3')).toHaveCount(0)`，且整张卡可见文字不含任何完整病史/诊断/答案标记。

**② 接上真实大模型（此前一直没生效——根因是 `.env` 未被加载 + 读错环境变量）**
- `backend/.env` 里本就有 `DEEPSEEK_API_KEY/BASE_URL/MODEL`（`deepseek-v4-flash`），但 `app.py` 从不加载 `.env`，且 `ai_service.py` 读的是 `OPENAI_*`（不是 `DEEPSEEK_*`），因此一直走 Mock。
- 修复：`app.py` 启动时 `_load_dotenv()` 加载 `backend/.env`；`ai_service.py` 改为读 `DEEPSEEK_*`（并以 `OPENAI_*` 兜底）；新增 `LLM_MOCK=1` 开关强制走 Mock（供确定性 e2e 门禁）。
- **LLM_MOCK 仅进程级、不持久**：只写在 `frontend/playwright.config.ts` 的 e2e webServer 命令里（`LLM_MOCK=1 …`），不写入 `.env`、不写 shell、不影响用户正常启动。用户以 `python app.py` / `start-backend.bat`（均不带 LLM_MOCK）启动时，`app.py._load_dotenv()` 加载 `.env` → 直接用真实 DeepSeek。
- **运行时确认**：`/api/health` 新增 `llm` 字段（`mode: real|mock`、`model`、`base_url`、`reason`），启动后 `curl http://127.0.0.1:5000/api/health` 即可确认是否联通真实大模型（如 `{"llm":{"mode":"real","model":"deepseek-v4-flash",...}}`）。
- 实测：真实 DeepSeek（`deepseek-v4-flash`）下，SP 能按问题给出自然的患者口吻回答（主诉/疼痛性质/加重缓解因素各不相同），**不主动泄露诊断**；考官按规则说英文；判卷出分/报告正常。e2e 门禁后端以 `LLM_MOCK=1` 启动（确定性）；`content-leak.spec.ts` 回复长度断言放宽到 <1000 以兼容真实回复。

### 参考：旧 REGRESSION 记录（已解决）

**现象（用户报告，已复现）：**
1. 开始界面（首页病例卡片）直接显示了完整病历/患者脚本——卡片本应只显示简短病例简介。
2. 进入对话后，患者开场/回复**直接把整个病例（近似答案）报出来**——本应只按需回答被问到的内容。

**根因（内容放置导致）：** 本次把 `summary` 字段从不超 ~30 字的简短简介改成了**完整大病历**（一般情况/主诉/现病史/既往史/系统回顾/个人史/家族史/婚育史/月经史等），而系统里 `summary` 同时被两处直接暴露：
- `frontend/app/components/Index/CaseBox.vue` 用 `{{ caseItem.summary }}` 渲染病例卡片（`line-clamp-3`）——现在卡片显示的是完整病历，即"patient prompt + 诊断暗示"。
- `backend/ai_service.py` 的 **Mock** 病人路径（`llm_configs` 表为空、`app.py` 不加载 `.env`、`OPENAI_/DEEPSEEK_` 未注入 → 走 Mock）在开场消息返回 `f"医生您好，我最近确实不舒服。简单说就是：{summary}"`——`summary` 现在是完整病历，所以病人一开场就把整个病例/答案全报出来了。

**相关数据/代码：** `backend/osce.db`、`backend/seed_data.py`（13 例，12 例 summary 已扩为完整大病历）、`case_content/*.md`、`backend/compile_case_content.py`（md→summary/reference_answer）；`backend/prompts.py`（patient_system_prompt 用 `summary` 作 SP scenario）；`backend/ai_service.py` `patient_reply` mock 分支；`frontend/app/components/Index/CaseBox.vue`（卡片渲染 summary）。`reference_answer`（现为完整答案）只在**报告页** `report/[sessionid].vue` 的 AnswerBox 渲染（评分后展示），不在卡片/对话中渲染，但**每个 session 响应都以 `include_case=True` 返回**它，前端未在前台展示故非本泄漏主因。

**修复方向（供下一个 agent 参考，非本次实施）：** 病历完整性内容不应放在会被"卡片 + 病人 mock 开场"直接暴露的 `summary` 里。建议：① 保持 `summary` 为简短病例简介（卡片用）；② 完整病历/病人剧本另存（新字段或独立结构化区），仅供 `patient_system_prompt` 使用并靠 prompt 规则约束"只答被问、不主动泄露"，且 **mock 开场不能回吐 summary**；③ `reference_answer` 维持"评分后参考答案"定位；④ 用独立 evaluator 子代理跑 `cd frontend && bash e2e.sh` 并把"病例卡片/对话开场不泄露诊断"纳入断言。修复后需重新往返 seed_data.py 与 osce.db。

### This Session — 12 例教学病例内容完善与指南校准（内容/文本任务，非代码）

- [x] 确认基线：`bash init.sh` 通过（backend import + db init + nuxt prepare）；cases 表 13 例（12 内置 + GP-003）。
- [x] 建立内容规范 `case_content/_TEMPLATE.md`：SUMMARY=患者口吻完整大病历（一般情况/主诉/现病史/既往史/手术外伤史/过敏史/用药史/系统回顾/个人生活史/家族史/婚育史/月经史，不含诊断/查体/辅助检查客观结果）；REFERENCE_ANSWER=完整教学答案（病例概览/诊断/鉴别诊断/体格检查/辅助检查应查vs特定指征/处理与管理(药物·非药物·随访)/问题清单/结局/结构化问答≥5道/指南依据）。
- [x] 用 **AgentTeams** 为 12 个 case 各派一个独立子代理（8 个成员、12 个任务，成员完成后再认领剩余任务），每例独立 `web_search` 检索该病种最新中国+国际指南并逐项校准，产出写入 `case_content/<case_no>.md`。12 例全部完成。
- [x] 指南校准覆盖面：CAP（中国 CAP 2016/基层 2018、IDSA/ATS 2019、NICE NG250）、T2DM（中国 2020/2024、ADA 2025、二甲双胍共识 2023、WHO/IDF）、阑尾炎（WSES Jerusalem 2020、中国 2020、SAGES 2024）、胆囊炎（TG18 I 级、中国胆道）、异位妊娠（ACOG PB193、NICE NG126、中国 2021）、子痫前期（ISSHP 2018、ACOG PB222 2020、NICE NG133、中国 2020）、婴幼儿腹泻（WHO、NICE CG84、ESPGHAN/ESPID 2014、中国 2024）、哮喘（GINA 2024/2025、中国 2016、NAEPP 2020、中国行动计划）、高血压（中国、ESC/ESH、ACC/AHA、OSA 排查）、GERD（中国 2022、Lyon 2.0 2023、ACG 2022、AGA 2024、WGO）、抑郁（中国 2025、NICE NG222、APA 2019、DSM-5/ICD-11）、惊恐（中国焦虑 2 版、NICE CG113、APA、WHO mhGAP、RANZCP 2018）。
- [x] 内容管线：新增 `backend/compile_case_content.py`（编译 md→summary/reference_answer）、`backend/regenerate_seed.py`（重组 seed_data.py 13 例）、`backend/update_case_content.py`（就地更新 osce.db 12 例）。
- [x] `backend/seed_data.py` 更新为 13 例（12 例换 enriched summary/reference_answer + GP-003 从 DB 保留）；`osce.db` 就地更新 12 例（summary 1071~1794、reference_answer 6013~12080 字符），GP-003 保持参考示例内容。
- [x] 校验：`/api/cases` 返回 13 例且 reference_answer 为完整教学答案；`bash init.sh` 通过；app import OK。
- [x] 启动后端 :5000（Flask）与前端 :3000（Nuxt 生产构建）供用户亲自端到端审核验证（本任务为内容/文本性质，按用户指示不跑 evaluator e2e）。

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
