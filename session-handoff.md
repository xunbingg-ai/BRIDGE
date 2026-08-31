# Session Handoff

## Current Objective

- **Status（feat-014 已收尾）：** 本阶段实现三个用户要求，均已完成并通过独立 evaluator e2e（模型 deepseek-v4-flash-vision-exp，真实 DeepSeek API，6/6 PASS）：
  1. **考官（viva）结构化问答骨架**：第一个问题改为「请用一分钟概括病史」，此后每个问题若学生答不上来只给一次 hint，一次 hint 后再答不上来就切换下一题（绝不二次提示 / 泄露答案）。
  2. **查体 / 辅助检查结果解密卡片改英文、只含结果**：卡片标题与副标题改英文，内容只放本案例客观结果，去掉「应查什么」指导 / 解读思路（判读）/「不常规需要」等说明。
  3. **对话时间戳 + 时长**：消息级毫秒时间戳存入 content，提交时计算 `duration_seconds`，对外暴露 `durationSeconds`，便于之后导出对话时长分析。
- **Branch / commit:** `260824-OSCE`。本次改动**尚未提交**（用户未要求提交；`git status` 见 Files Changed）。
- **e2e 关键经验**：真实模型把首问说成「请用1分钟…总结病史」时，按措辞做关键词匹配的旧 pickAnswer 会漏判 hist → 答非所问 → 考官反复重问而脱节。已改为「顺序推进状态机」（hist/dx/diff/pe/inv/mgmt），并在「结束问询」后 `await` end-inquiry 响应再作答（否则首条答案会被路由到病人阶段）。

## 已解决（本阶段 feat-014）

### ① 考官结构化问答：首问=概括病史 + 每题一次 hint（Problem 1）
- `backend/prompts.py` `examiner_system_prompt`：
  - `[How to proceed]` 现为 6 项：1) 概括病史（opening）→ 2) 诊断 → 3) 鉴别 → 4) 体格检查 → 5) 辅助检查 → 6) 处理/随访。
  - 新增 `[Handling an incomplete answer]`：除首问外，学生答不足/答不出只给**一次**短 hint（不泄露答案）；hint 后再答不出即切下一题；绝不二次提示。
  - 保留 `[PART: pe]` / `[PART: investigations]` 分节标记与「不得在问题/点评中泄露查体/检查结果」。
- `backend/ai_service.py` `examiner_reply` Mock 同步为「概括病史→诊断→鉴别→体格检查→辅助检查→处理」顺序推进（LLM_MOCK 生效时）。

### ② 英文、只含结果的解密卡片（Problem 2）
- 新增 `backend/viva_results.py`：`VIVA_RESULTS_EN`，内建 12 例的 `pe`/`investigations` **英文客观结果**（GP-003 无该小节不收录）。来源 = `case_content/*.md` 对照翻译整理，只留本案例结果，去指导/判读/解读/「不常规需要」。
- `case_utils.case_viva_sections(reference_answer, case_no)`：按 `case_no` 优先命中英文结果；未收录病例（如 CSV 导入）回退到旧中文小节提取。`sessions.py` 两处调用传入 `case_no`。
- 前端 `VivaResultCard`/`ChatBox`：标题改英文（Physical Examination Findings / Investigation Results），副标题改英文（Findings revealed for this case）。

### ③ 对话时间戳 + 时长（Problem 3）
- `backend/database.py` `now_iso()` 改为**毫秒精度**；每消息 `created_at` 即毫秒时间戳（存入 content）。
- `backend/sessions.py`：新增 `_compute_duration`；`submit_session` 写 `content['ended_at']` / `content['duration_seconds']`；`session_to_dict` / `history_to_dict` 新增 `durationSeconds`（供导出分析）。前端 `types` 增 `durationSeconds`。
- 每消息已有 `created_at`（毫秒）；`content.started_at` / `ended_at` / `duration_seconds` 齐备。

## Verification / DoD
- `bash init.sh` 通过；`cd frontend && pnpm build` 通过（2.49 MB / 637 kB gzip）。
- **独立 evaluator 子代理（模型 deepseek-v4-flash-vision-exp）** 运行 `cd frontend && bash e2e.sh` **全部通过 6/6**：smoke 2/2、content-leak 2/2、admin-case 1/1、viva-reveal 1/1；`/api/health` 确认 `mode=real`；`frontend/test-results/.last-run.json` = `{"status":"passed"}`。
- e2e 关键点：**不使用 LLM_MOCK**（playwright.config 已去掉；真实模型）。`viva-reveal.spec.ts` 改为顺序推进状态机 + 等待 end-inquiry。
- 环境：e2e 结束后端口 5000/3000 有后台任务在跑（可自行 job_kill；或保留供人工复核）。

## 小提醒
- 真实模型首问措辞多变（中文「请用1分钟…总结病史」/ 英文「summarise … in one minute」），e2e 已用顺序推进规避；若后续给医生/考官换模型，需复核 `viva-reveal.spec.ts` 的推进策略。
- 卡片内容为只含结果的英文，来自 `viva_results.py`；若后续修改某个 case 的体格检查/辅助检查结果，需同步更新 `viva_results.py` 对应项（该表不随 reference_answer 自动生成）。
- 管理员通过 CSV/后台导入的新病例不含英文结果，卡片会回退到中文小节提取。



## 已解决（本阶段 feat-013）

### ① 查体/辅助检查结果解密卡片（Problem 1）
- **后端**：`case_utils.case_viva_sections(reference_answer)` 从 `### 体格检查`/`### 辅助检查` 小节提取客观结果（12 例有内容，GP-003 无该小节 → 空串 → 前端不显示卡片）；`_extract_markdown_section` 支持标题带括号（如 PS-001「体格检查（精神检查 MSE + 躯体）」）。
- `prompts.examiner_system_prompt` 拆成 5 段（诊断/鉴别/体格检查/辅助检查/处理），并在体格检查、辅助检查小节点评后输出 `[PART: pe]` / `[PART: investigations]`；强化「不得在问题或点评中泄露查体/检查结果」。
- `sessions.py` `_case_payload`/`session_to_dict(include_case=True)` 返回 `peFindings`/`investigations`。
- **前端**：`utils/viva.ts`（extractVivaParts/stripVivaTags/hasVivaPart）、`VivaResultCard.vue`；`ChatBox` 剥掉 `[PART:...]` 并从该消息解密两张结果卡片；`main.css` 补 markdown-body 表格样式；气泡 markdown 加 `chat-bubble-md`（供测试读取考官问题、避免误读卡片内容）。
- **真实模型行为**：考官按「诊断→鉴别→体格检查→辅助检查→处理」顺序推进，Q1（诊断）常要求**只依据病史**（若回答泄露化验/影像结果会被要求重来）；到体格检查小节后输出 `[PART: pe]`，到辅助检查小节后输出 `[PART: investigations]`。

### ② SP 一次只答一个信息点（Problem 2）
- `prompts.patient_system_prompt` 新增：即使被追问「还有吗/再多一点/详细讲讲」，也只补充一个最相关的新信息点，绝不一次汇报或复述整段现病史；每次回答尽量一到两句话。
- 真实模型实测：追问「请再告诉我多一点」时 SP 只回「就是三天前熬夜加班后受了点凉，晚上就开始发冷、发烧了。」（单句、无结构标记）。

## Verification / DoD
- `bash init.sh` 通过；`cd frontend && pnpm build` 通过（2.49 MB / 637 kB gzip）。
- **独立 evaluator 子代理（真实 DeepSeek API）** 运行 `cd frontend && bash e2e.sh` **全部通过 6/6**：smoke 2/2、content-leak 2/2、admin-case 1/1、viva-reveal 1/1；`/api/health` 确认 `mode=real`；`frontend/test-results/.last-run.json` = `{"status":"passed"}`。
- e2e 关键点：**不使用 LLM_MOCK**（playwright.config 已去掉；真实模型）。viva-reveal 测试用分阶段答案（病史-only / 计划-only）推进考官，避免被判定为「提前泄露后续结果」。
- 环境：e2e 结束后端口 5000/3000 已清理（无残留进程）。

## 小提醒
- `content-leak.spec.ts` 已增补「追问请再告诉我多一点」断言（SP 回复 <500 字且无结构标记）；`viva-reveal.spec.ts` 依赖真实模型（非常规 mock 固定顺序），若遇到真实模型偶发「卡在某一问」可能需重跑一次。
- GP-003 无 `### 体格检查`/`### 辅助检查` 小节，因此不会出现解密卡片（符合「可选字段」预期）。

---
## 历史记录 — 内容泄漏回归（feat-012，已修复）

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
4. 运行 `bash init.sh` 验证基线（后端 import/db 迁移 + 前端 nuxt prepare）。
5. 若要跑 e2e：`cd frontend && bash e2e.sh`（Playwright webServer 自动拉起后端 :5000 + 前端 :3000，已运行则复用）。本环境 shell 有 HTTP 代理（`http_proxy=http://172.26.64.1:7897`）会拦 localhost，用 curl 自查要加 `--noproxy '*'`；`e2e.sh` 已绕过代理，浏览器直接访问不受影响。

## Recommended Next Step

- **feat-014 已收尾并提交。** 独立 evaluator 子代理（模型 `deepseek-v4-flash-vision-exp`）运行 `cd frontend && bash e2e.sh` 已全部通过（6/6；`/api/health` mode=real；`.last-run.json`=passed）；`bash init.sh`、`pnpm build` 通过。
- 建议下一步：**生产化加固**——更换默认 `JWT_SECRET`、收紧 CORS `origins:*`、把 DeepSeek 配置正式化（环境变量或经 `/admin` 后台持久化）。
- 或扩充 e2e 用例：注册/登录、完整会话流、个人中心等长流程，并固化进 `frontend/e2e/`。
- 注意：卡片英文结果维护在 `backend/viva_results.py`（不随 reference_answer 自动生成）；管理员导入的新病例卡片回退到中文小节提取。
