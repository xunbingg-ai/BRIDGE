# Session Handoff

## Current Objective

- **Status（feat-012 已收尾）：** 上阶段按 `Example teaching case(2).md` 完善 12 例教学病例并引入「内容泄漏」回归；**本阶段已按用户更贴近真实 OSCE 的方案修复完毕**（见下方「REGRESSION — 内容泄漏（已修复）」）。
- **修复结果：** `summary` 改为 `patient_scenario`（内容不变，DB 就地迁移）；卡片只显示派生的 OSCE 开场信息（年龄+性别+一个核心症状）；对话由学生先开口（取消 SP 开场自动气泡）；病人/考官 prompt 与卡片 API 均不泄露完整病历与答案。
- **Branch / commit:** `260824-OSCE` @ `78f153d`（工作区含本次修复 + 内容改动，尚未提交）。

## REGRESSION — 内容泄漏（**已修复**，本阶段收尾）

### 原现象（已确认）
1. 开始界面（首页病例卡片 `CaseBox.vue`）直接显示了完整大病历（= patient prompt + 诊断暗示），卡片本应只显示简短病例简介。
2. 进入对话后，病人开场/回复直接把整个病例（近似答案）报出来，而不是"按需回答被问到的内容"。

### 根因
`summary` 字段这次被从 ~30 字简短简介改成了**完整大病历**。而 `summary` 在两个地方被原样暴露：
- **卡片**：`frontend/app/components/Index/CaseBox.vue` 用 `{{ caseItem.summary }}`（`line-clamp-3`）渲染病例卡片 → 现在显示完整病历。
- **病人 Mock 开场**：`backend/ai_service.py` 的 Mock 分支（`llm_configs` 表为空、`app.py` 不加载 `.env`、`OPENAI_/DEEPSEEK_` 未注入 → 走 Mock）在开场消息返回 `f"医生您好，我最近确实不舒服。简单说就是：{summary}"` → `summary` 是完整病历，所以病人一开场就把整个病例/答案全吐出。

`reference_answer`（现为完整答案）只在**报告页** `report/[sessionid].vue` 的 AnswerBox 渲染（评分后展示），不在卡片/对话中渲染，故非本泄漏主因；但它也随每个 session 响应以 `include_case=True` 返回，前端未在前台展示。

### 相关文件
- `backend/seed_data.py`（13 例，12 例 summary 已扩为完整大病历）
- `backend/osce.db`（12 例就地更新）
- `case_content/<case_no>.md`（每例内容源 + 指南依据）
- `backend/compile_case_content.py`（md → summary/reference_answer）、`backend/update_case_content.py`（写库）、`backend/regenerate_seed.py`（重组 seed_data.py）
- `backend/prompts.py`（`patient_system_prompt` 用 `summary` 作为标准病人 scenario）
- `backend/ai_service.py`（`patient_reply` Mock 分支回吐 `summary`）
- `frontend/app/components/Index/CaseBox.vue`（卡片渲染 `summary`）
- `frontend/app/pages/report/[sessionid].vue`（`referenceAnswer` 只在报告页展示）

### 修复方向（供 refer，非本轮实施）
1. **保持 `summary` 为简短病例简介**（卡片用，~1 句，不泄露诊断/完整病史）。
2. 完整大病历/病人剧本**另存**（新增字段或独立结构化区，如 `patient_scenario`/`sp_script`），只在 `patient_system_prompt` 使用，并靠 prompt 规则约束"只答被问、不主动泄露诊断/检查结论"，同时**不能让 mock 开场回吐该内容**。
3. 若已配置真实 LLM（`llm_configs` 或 `OPENAI_API_KEY`/`DEEPSEEK_*`），也需确保病人靠 prompt 规则不提前泄露（真实模型当前未被启用；`.env` 未由 app.py 加载，需确认启动方式是否注入 env）。
4. `reference_answer` 维持"评分后参考答案"定位（报告页展示即可）。
5. 修改后，重新编排 `seed_data.py` 与 `osce.db` 内容（把"完整病历"从 `summary` 中移出），并**跑独立 evaluator 子代理 `cd frontend && bash e2e.sh`**，新增断言：病例卡片与对话开场**不出现**诊断/完整病史关键词。

### 修复后验证（AGENTS.md 端到端门禁）
- 独立 evaluator 子代理（全新上下文）运行 `cd frontend && bash e2e.sh` 全部通过。
- 断言升级：首页病例卡片仅显示简短简介；进入会话后病人开场只给一句自然问诊，不吐诊断/完整病历；评分后报告页正常展示参考答案。
- `bash init.sh` 通过；`git status` 确认改动范围。

## Work Completed This Session — feat-012（12 例病例内容完善 + 指南校准）

- [x] 建立内容规范 `case_content/_TEMPLATE.md`（SUMMARY=患者口吻完整大病历；REFERENCE_ANSWER=完整教学答案 + ≥5 道结构化问答 + 指南依据）。
- [x] 用 **AgentTeams** 为 12 个 case 各派独立子代理（8 成员、12 任务，成员完成后认领剩余任务），每例独立 `web_search` 检索该病种最新中国+国际指南并逐项核查校准，产出写入 `case_content/<case_no>.md`（12 例全部完成，产物高质：诊断标准/分级/检查选择/治疗方案/随访均按最新指南，如 CAP CURB-65、T2DM ADA2025+中国2024、阑尾 WSES Jerusalem 2020、胆囊 TG18、异位妊娠 ACOG PB193、子痫前期 ISSHP/ACOG PB222、腹泻 WHO/NICE/中国2024、哮喘 GINA、高血压中国/ACC-AHA、GERD Lyon2.0/ACG2022、抑郁 NICE NG222/APA2019/中国2025、惊恐 NICE CG113/APA）。
- [x] 内容管线脚本（`backend/`）：`compile_case_content.py`（md→summary/reference_answer）、`regenerate_seed.py`（重组 seed_data.py 13 例）、`update_case_content.py`（就地更新 osce.db）。
- [x] `backend/seed_data.py` 更新为 13 例；`backend/osce.db` 就地更新 12 例；GP-003 保持参考示例内容（已对照 2021 AHA/ACC 胸痛指南核查看一致）。
- [x] `bash init.sh` 基线通过（backend import + db init + nuxt prepare）；`/api/cases` 返回 13 例且 reference_answer 为完整教学答案。
- [x] 启动后端 :5000（Flask 后台 job）、前端 :3000（Nuxt 生产构建后台 job）供用户亲自 e2e 审核。
- [x] **未运行 e2e**：本任务为纯内容/文本性质，按用户指示不需要独立 evaluator 子代理进行端到端验证，由用户完成后亲自审核。

## Work Completed This Session

- [x] **移除 `difficulty` 字段**：
  - `backend/schema.sql` `cases` 表删去 `difficulty` 列；`backend/seed_data.py` 12 例去掉 `difficulty`。
  - `backend/cases.py` `case_to_dict`/`case_detail_to_dict` 去掉 `difficulty`；`backend/admin.py` 校验/CRUD/导入/CSV 模板去掉 `difficulty`。
  - 前端 `types/index.ts`（`CaseSummary` 去 `difficulty`）、`CaseBox.vue`（去难度徽标）、`CaseManager.vue`（去「难度」列）、`CaseForm.vue`（去难度下拉）、`CsvUploader.vue`（CSV 模板去难度列）。
  - 对既有 `backend/osce.db` 做就地列迁移（`database._migrate_cases`，幂等 `ALTER TABLE ... DROP COLUMN`），保留 13 例既有病例 + 既有会话。
- [x] **统一 prompt 骨架（`backend/prompts.py`）**：
  - 新增 `patient_system_prompt(case)` / `examiner_system_prompt(case)` / `assessment_system_prompt(case, transcript)`，接口极小（case -> str 或 case+transcript -> str），模板构造/插值/规则封装在内（深度抽象）。
  - `ai_service.py`：`patient_reply`/`examiner_reply` 改用 `prompts.*`；`grade_session` 先 `_build_transcript(content)` 扁平化对话，再内联进 `assessment_system_prompt` 并发送固定 user 消息（对齐参考文档 §4.2）。
  - `sessions.py`：`_get_owned_session`/`_grade_and_save` 查询去掉 prompt 列、补 `c.case_no`；`_case_payload` 返回 title/department/summary/reference_answer/case_id/case_no。
  - `admin.py`、`cases.py`、`database.py`：去掉 patient/examiner prompt 相关字段写入。
  - 前端 `CaseForm.vue` 去「AI 病人/考官提示词」输入框；`CsvUploader.vue` CSV 模板去这两列；`types/index.ts` `CaseDetail` 去 `patientPrompt`/`examinerPrompt`。
  - 语言规则：SP 说中文、考官说英文（骨架中硬性规定），本次不做中英文切换。
- [x] 基线验证：`bash init.sh` 通过；`cd frontend && pnpm build` 全量构建通过（exit 0）。
- [x] **独立 evaluator e2e PASS（5/5）**：`cd frontend && bash e2e.sh` —— 官方病例全流程（注册学生 → 选病例 → 病人问询 → 结束问询 → 考官 → 提交 → `/report` 总分+四维+参考答案）、admin 管理（无「难度」列/字段）、导入新病例并删除、冒烟 2 项；全程无未捕获页面错误；导入用例与临时数据已清理。

## Verification Evidence

| Check | Command | Result | Notes |
|---|---|---|---|
| 基线验证 | `bash init.sh` | ok | backend import + db 迁移/init + nuxt prepare |
| 全量构建 | `cd frontend && pnpm build` | exit 0 | 2.49 MB / 636 kB gzip |
| 冒烟 e2e | `cd frontend && bash e2e.sh` | 2/2 passed | 病例列表 + admin 登录 |
| 独立 evaluator e2e | `cd frontend && bash e2e.sh` | 5/5 passed | 官方病例全流程 + admin 管理 + 导入新病例并删除 + 冒烟 2 项 |
| cases 表列 | `PRAGMA table_info(cases)` | 无 difficulty/patient_prompt/examiner_prompt | 仅 case_id/case_no/title/department/summary/reference_answer/is_active/created_at/updated_at |
| 病例数 | `select count(*) from cases` | 13 | 12 内置 + GP-003；导入用例已删（EVAL 行 = 0） |
| 导入清理 | `select count(*) where case_no like 'EVAL-%'` | 0 | 新导入病例已删除，病例库恢复 13 例 |
| 工作区 | `git status --short` | 见 Files Changed | 本次改动未提交；`docs/` 为参考文档（未跟踪） |

## Files Changed

- `backend/prompts.py` — **新增**：三个统一 prompt 骨架函数（深度抽象）
- `backend/schema.sql` — `cases` 表去 `difficulty`/`patient_prompt`/`examiner_prompt` 列
- `backend/seed_data.py` — 12 例去 `difficulty`/`patient_prompt`/`examiner_prompt`
- `backend/database.py` — `seed_cases` 去字段 + 新增 `_migrate_cases`（就地删列迁移）
- `backend/cases.py` — `case_to_dict`/`case_detail_to_dict` 去 `difficulty` + prompt 字段
- `backend/ai_service.py` — `patient_reply`/`examiner_reply`/`grade_session` 改用 `prompts.*` + `_build_transcript`
- `backend/sessions.py` — `_get_owned_session`/`_grade_and_save` 查询与 `_case_payload` 去除 prompt 列、补 `case_no`
- `backend/admin.py` — 校验/CRUD/导入/CSV 模板去 `difficulty` + prompt 字段
- `frontend/app/types/index.ts` — `CaseSummary`/`CaseDetail` 去 `difficulty`/`patientPrompt`/`examinerPrompt`
- `frontend/app/components/Index/CaseBox.vue` — 去难度徽标
- `frontend/app/components/admin/CaseManager.vue` — 去「难度」列
- `frontend/app/components/admin/CaseForm.vue` — 去难度下拉 + AI 病人/考官提示词输入框
- `frontend/app/components/admin/CsvUploader.vue` — CSV 模板去 `difficulty`/`patient_prompt`/`examiner_prompt`
- `feature_list.json` — 新增 feat-011（done）；`progress.md` — 本会话记录

## Decisions Made

- **病例表只保留内容字段**：`difficulty`、`patient_prompt`、`examiner_prompt` 三列已从 schema 与存量 osce.db 删除；prompt 由 `backend/prompts.py` 从 `title/department/summary/reference_answer` 运行时组装。
- **`osce.db` 就地迁移而非重建**：`_migrate_cases` 用 `ALTER TABLE ... DROP COLUMN`（SQLite 3.51 支持），幂等，保留 13 例与既有会话，随 `init_db()` 自动执行。
- **评估评分体系不变**：仍为 100 分四维（病史采集 30 / 沟通 25 / 临床推理 25 / 职业素养 20），仅把评分指令收敛进 `assessment_system_prompt`，前端 ScoreBox/AnswerBox 无需改动。
- **语言规则硬编码**：SP 说中文、考官说英文（骨架内规定，本次不做双语切换）。
- **不做前身 repo 的高级特性**：viva 分节 tag（`[PART: ...]`）与 PE/检查结果解密卡片、`sp_script` 等本仓库当前没有的能力，未引入，保持最小改动。

## Blockers / Risks

- 无阻塞项；本会话改动已通过独立 evaluator e2e（5/5）。
- `JWT_SECRET` 仍为默认 `dev-secret-*`，生产需更换。
- CORS `origins: *`，上线前需收紧。
- DeepSeek key 靠环境变量注入、未落盘；未配置时降级为内置 Mock（e2e 走 Mock 稳定；真实 LLM prompt 组装冒烟未在 e2e 覆盖，本次仅以函数实测为准）。
- `docs/prompt-architecture_from_previous.md` 为参考文档，未跟踪（`docs/` 未入库），勿提交。

## Next Session Startup

1. `pwd` 确认工作目录为仓库根 `/mnt/d/BRIDGE`。
2. Read `AGENTS.md`（启动流程、工作规则、完成定义、端到端验证门禁）。
3. Read `feature_list.json`（功能状态事实来源）与 `progress.md`（本会话日志）。
4. **先读本文件「REGRESSION — 内容泄漏」段**：这是当前最优先要修的问题。
5. 运行 `bash init.sh` 验证基线（后端 import/db 迁移 + 前端 nuxt prepare）。
6. 当前后端 :5000、前端 :3000 有后台任务在跑（job bash-3 / bash-4，内容已写入但泄漏未修），可用 `job_kill` 停掉后重新启动；本环境 shell 有 HTTP 代理（`http_proxy=http://172.26.64.1:7897`）会拦 localhost，用 curl 自查要加 `--noproxy '*'`，浏览器直接访问不受影响。

## Recommended Next Step

- **feat-012 已收尾（无需再修内容泄漏）。** 独立 evaluator e2e（`cd frontend && bash e2e.sh`，含 `smoke.spec.ts` + `content-leak.spec.ts`）已全部通过；`bash init.sh`、`pnpm build` 通过。
- 提交本阶段改动：`git add`（`backend/` 本案代码 + `case_utils.py`、内容管线脚本、`frontend/` 本案代码 + `e2e/content-leak.spec.ts`、`case_content/`、`feature_list.json`、`progress.md`、`session-handoff.md`、`.gitignore`），`git commit` 并 push 到 `origin/260824-OSCE`。`docs/` 为参考文档（未入库，可 gitignore）。
- 后续可做生产化加固：更换默认 `JWT_SECRET`、收紧 CORS `origins:*`、正式化 DeepSeek 配置；或扩充 e2e 用例（注册/登录、完整会话流、个人中心）。
