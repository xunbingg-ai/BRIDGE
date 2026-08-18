# 任务分解与验收标准

本文档把 `feature_list.json` 中剩余的首期 feature 分解为可独立交付的子任务。**每个子任务都有明确的验收标准**；未达到验收标准不得标记完成。全局验收门槛见文末。

依赖关系（feature 级）：

```
feat-010 病例数据模型+种子  ← 当前推荐（依赖 feat-001 ✓）
feat-011 DeepSeek 适配      ← 依赖 feat-001 ✓
feat-002 登录               ← 依赖 feat-001 ✓
feat-003 病例列表           ← 依赖 feat-010
feat-004 CCE 考站流程壳     ← 依赖 feat-003
feat-005 AI 问诊            ← 依赖 feat-004, feat-011
feat-006 病例汇报           ← 依赖 feat-004
feat-007 结构化问题+检查揭示 ← 依赖 feat-004
feat-008 评分反馈           ← 依赖 feat-004, feat-007, feat-011
feat-009 教师统计           ← 依赖 feat-002, feat-004
```

里程碑 **M1 演示版**（一个月内给老师演示）＝ feat-002 + feat-003 + feat-004 + feat-005 + feat-006 + feat-007 + feat-008 + feat-009 完成、且用 Cecilia 病例（feat-010）跑通完整流程。

---

## feat-010 病例数据模型与开发者录入工作流

**T-010.1 领域数据模型**
内容：按需求 §9 与 Excel 模板定义 SQLAlchemy 模型：`Case`（id/title/type/systemTags/difficulty/languageAvailability/learningObjectives/studentInstructions/status）、`PatientInformation`（基本信息/主诉/HPI/ROS/PMH/PSH/用药/过敏/家族史/个人史/性史/妇产史/openingStatement/affectStyle/ICE/disclosureRules/qaTriggers）、`ExaminerPack`（caseSummary/workingDiagnosis/differentials/structuredQuestions/suggestedAnswers/physicalExamRelease/investigationRelease/scoringRubric）、`CaseReviewRecord`（caseId/reviewStatus/reviewerName/reviewComment/reviewedAt/publishedAt）。
验收标准：
- 模型类与关系在 `backend/app/models/` 下，字段与需求 §9 一一对应（有映射注释）
- 用例覆盖模型创建/关系/枚举校验，`uv run pytest` 全绿
- `CONTEXT.md` 术语在模型命名中保持一致（Case、Structured Question、Investigation Result、Rubric…）

**T-010.2 数据库迁移**
内容：接入 Alembic，生成首个可重复的迁移。
验收标准：
- `backend/alembic/` 存在，`uv run alembic upgrade head` 在空 SQLite 上成功
- `uv run alembic downgrade base` 后可再 upgrade，往返无损

**T-010.3 病例结构化文件格式**
内容：定义病例 JSON 文件的 schema（`backend/cases/schema.py` 或 Pydantic 模型），字段对齐 Excel 模板；含"脱敏"校验规则（不允许真实姓名/证件号等字段）。
验收标准：
- Pydantic schema 能校验合法病例文件、拒绝缺字段/非法枚举的文件
- 文档 `docs/case-file-format.md` 说明每个字段与 Excel 模板的对应
- **DEFERRED (2026-08-18):** ~~校验器明确拒绝可识别身份信息（规则来自 ADR-0002）~~ 用户决策：本期病例全为虚拟病例；加入真实病例前由用户亲自校验脱敏；ADR-0002 政策保留。

**T-010.4 种子脚本与 Cecilia 病例**
内容：`backend/scripts/seed_cases.py` 读取 `cases/` 目录并导入数据库；把 Cecilia 示例（GP-ChestPain-0001）完整转成首个种子文件。
验收标准：
- 运行种子脚本后，数据库中出现 GP-ChestPain-0001（status=published），包含 7 道结构化问题、检查项与 rubric
- 重复运行种子脚本不产生重复数据（幂等）
- 种子文件内容与 `Example teaching case.md` 一致（可对照抽查）

**T-010.5 导入测试**
内容：为 schema、种子脚本、幂等性写测试。
验收标准：
- `uv run pytest` 全绿；新增用例 ≥ 5 个
- 一条失败路径被覆盖（例如非法病例文件被拒绝且不污染数据库）

## feat-011 DeepSeek V4 Flash 适配层

**T-011.1 Provider 客户端**
内容：`backend/app/services/llm/client.py`：读 `DEEPSEEK_API_KEY`，`base_url=https://api.deepseek.com`，模型 `deepseek-v4-flash`；无 key 时启动失败但给出清晰报错（或 mock 模式）。
验收标准：
- 配置来自环境变量，无硬编码密钥
- 单元测试用 mock 客户端验证调用参数（model/base_url 正确）

**T-011.2 标准化病人对话模块**
内容：`backend/app/services/sp/`：系统提示词从 `backend/app/prompts/sp_*.txt` 加载；严格按病例脚本回答、禁止编造检查结果、禁止主动给出诊断。
验收标准：
- 传入病例脚本后，mock 响应按提示词模板生成请求体
- 提示词文件包含"只依据脚本回答""不编造结果"约束（ADR-0002 合规）
- 测试覆盖：脚本外问题不产生虚构信息（用 mock 验证 prompt 内容）

**T-011.3 评分模块**
内容：`backend/app/services/scoring/`：按 rubric 生成评分提示词，要求 JSON 输出（分数/反馈/参考答案）；无 rubric 的病例拒绝评分。
验收标准：
- 输出被 Pydantic 模型校验（score/feedback/reference_answer）
- 无 rubric 时返回明确错误，不产生分数

**T-011.4 流式接口**
内容：后端 SSE/WebSocket 端点把 SP 回复流式给前端。
验收标准：
- 端点在 mock 流下返回 `text/event-stream`，前端可逐块渲染
- 测试覆盖端点状态码与首个事件

## feat-002 学生/教师登录

**T-002.1 User 模型与密码**
内容：`User`（username/role: student|teacher|admin/password_hash/created_by）；密码用强哈希（bcrypt/argon2）。
验收标准：
- 密码不存明文；测试断言数据库无明文
- 角色枚举受保护

**T-002.2 管理员创建账号**
内容：CLI 脚本 `backend/scripts/create_user.py`（管理员可建学生/教师账号）。
验收标准：
- 脚本可创建账号并写入数据库；重复用户名报错

**T-002.3 登录/登出 API**
内容：POST `/api/auth/login`、POST `/api/auth/logout`、GET `/api/auth/me`；session cookie。
验收标准：
- 正确凭据返回 200 + session；错误凭据 401
- 未登录访问受保护路由返回 401

**T-002.4 前端登录页与守卫**
内容：英文登录页 + 路由守卫（学生/教师各自可访问范围）。
验收标准：
- 登录后可进入病例列表；未登录被重定向到 /login
- `npm run typecheck` 干净

## feat-003 可练习病例列表

**T-003.1 病例列表 API**
内容：GET `/api/cases`（仅 published、登录学生可见），返回标题/难度/语言/学习目标等。
验收标准：
- 未登录 401；登录后返回 published 病例；草稿/审核中病例不可见
- pytest 覆盖上述三条

**T-003.2 前端病例列表页**
内容：英文页面展示病例卡片，可点击进入考站。
验收标准：
- 从 API 渲染列表；空状态/加载状态可见
- typecheck + build 通过

## feat-004 CCE 考站流程壳

**T-004.1 PracticeSession 状态机**
内容：`PracticeSession`（user/case/current_section/status: in_progress|completed/answers…）；section 顺序：student instruction → history taking → case presentation → structured questions → scoring；仅允许顺序推进、禁止回看已完成 section；支持中断后继续。
验收标准：
- 状态机测试覆盖：顺序推进、越界拒绝、续练恢复、完成后不可再改
- `uv run pytest` 全绿

**T-004.2 前端考站布局与进度**
内容：考站页面：左侧/顶部 section 导航（锁定未解锁项）、内容区、退出续练入口。
验收标准：
- 刷新页面后进度保持（从服务端恢复）
- 未解锁 section 不可点击

**T-004.3 语言规则**
内容：每个 section 按病例配置语言（en/zh），同 section 内禁止混用（校验 + 提示）。
验收标准：
- 配置为英文的 section，前端提交时拒绝中文输入并提示（反之亦然）
- 测试覆盖中英混用拒绝

## feat-005 AI 标准化病人问诊

**T-005.1 聊天界面与流式**
内容：前端聊天窗（消息列表、输入框、打字机效果、加载态），对接流式接口。
验收标准：
- 学生消息/SP 回复按序展示；流式渲染可见
- 发送中禁止重复提交

**T-005.2 SP 会话后端**
内容：按 `PracticeSession` 保存问诊消息；每次调用携带病例脚本上下文；SP 不越权。
验收标准：
- 消息持久化，刷新后可恢复
- 测试：SP 响应仅来自脚本内容（mock 断言 prompt 含脚本、不含答案）

## feat-006 病例汇报

**T-006.1 汇报输入与保存**
内容：Case presentation 阶段：文本区 + 语言校验 + 保存到会话。
验收标准：
- 汇报按语言规则校验；保存后可在评分阶段看到
- pytest/typecheck 通过

## feat-007 结构化问题与检查结果揭示

**T-007.1 逐题作答**
内容：结构化问题逐题展示，答完一题解锁下一题；答案持久化。
验收标准：
- 当前题作答前下一题不可见；刷新不丢已答内容

**T-007.2 检查请求匹配**
内容：学生在作答时提出检查需求 → 后端在病例检查库匹配；命中展示结果，未命中提示 "The result is pending / not provided"；**禁止 AI 编造**。
验收标准：
- 命中/未命中两条路径均有测试；未命中响应文案固定
- 展示的结果只能来自病例配置数据

**T-007.3 结果固定面板**
内容：已揭示的检查结果显示在当前页面右侧/下方，后续问答可随时回看。
验收标准：
- 页面状态回显全部已揭示结果；刷新后仍保留

**T-007.4 补充揭示信息**
内容：完成全部结构化问题后，按病例配置揭示 provided information/标准报告。
验收标准：
- 仅在全部问题完成后出现；内容来自病例配置

## feat-008 AI 评分、反馈与参考答案

**T-008.1 评分调用与解析**
内容：会话完成后触发评分（rubric + 学生全部作答），解析 JSON 输出。
验收标准：
- 评分结果（score/feedback/reference answers）持久化
- 无 rubric 病例不评分（明确提示）

**T-008.2 结果页**
内容：完成页展示参考分、AI 反馈、参考答案、教学解析；标记"练习参考"。
验收标准：
- 页面文案明确"practice reference score"；数据来自评分记录

## feat-009 教师端基础统计

**T-009.1 统计 API**
内容：教师可见：病例完成数、学生练习次数、完成率（无个人作答细节，符合首期范围）。
验收标准：
- 教师角色可访问、学生角色 403
- 统计口径有测试（种子数据断言数字）

**T-009.2 教师端页面**
内容：英文统计页（表格/卡片）。
验收标准：
- 页面渲染 API 数据；typecheck + build 通过

---

## 全局验收门槛（任何子任务标记完成前）

- [ ] 对应 feature 的所有子任务均满足各自的验收标准
- [ ] `bash init.sh` 全绿（后端 pytest + 前端 typecheck + build）
- [ ] 证据（命令与输出）写入 `feature_list.json` / `progress.md`
- [ ] 未引入未记录的新依赖或架构变更；若引入，补 ADR
- [ ] 术语与 `CONTEXT.md` 一致；病例内容不进日志；真人病例已脱敏
- [ ] 一次只做一个 feature；git 工作树干净并提交
