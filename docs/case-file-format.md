# 病例 JSON 文件格式（feat-010 T-010.3）

本文档定义开发者录入病例所用的 JSON 文件格式，字段与需求文档
《BRIDGE - 首期需求文档.md》第 9 节（Case / PatientInformation /
ExaminerPack / CaseReviewRecord）及 Excel 模板一一对应。

> **脱敏政策（2026-08-18 用户决策）**：本期所有病例均为虚拟病例，因此
> schema **不实现自动脱敏校验**（ADR-0002 政策保留）。日后加入真实病例时，
> 必须由用户本人亲自校验脱敏后再入库。

## 顶层字段 ↔ 需求 §9 Case

| JSON 字段 | 需求 §9 / Excel 模板 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `case_id` | Case ID | string | 是 | 唯一 ID，例如 `GP-ChestPain-0001` |
| `title` | Case Title | string | 是 | 病例标题 |
| `type` | Case Type | enum | 是 | `initial_visit` \| `follow_up_visit` |
| `system_tags` | systemTags | string[] | 否 | 系统标签，如 `["primary-care"]` |
| `difficulty` | difficulty | string | 是 | 难度（如 `medium`） |
| `language_availability` | languageAvailability | enum[] | 否 | 对外展示语言，`en` \| `zh` |
| `sections_language` | §7 per-section Language Rule | map | 是 | 每个 section 的语言，见下节 |
| `learning_objectives` | learningObjectives | string[] | 否 | 学习目标 |
| `student_instructions` | studentInstructions | string | 是 | 发给学生的任务说明 |
| `status` | status | enum | 否 | `draft` \| `in_review` \| `approved` \| `published`，缺省 `draft` |
| `patient_information` | §9.2 PatientInformation | object | 是 | 见下节 |
| `examiner_pack` | §9.3 ExaminerPack | object | 是 | 见下节 |
| `review_record` | §9.4 CaseReviewRecord | object \| null | 否 | 审核记录，可缺省 |

## `sections_language`（per-section 语言配置）

合法 key 固定为 5 个 section（与 CCE 流程一致），value 只能是 `en` 或 `zh`。
同一 section 内禁止混合语言；首期演示病例全部配置为 `zh`。

| key | 对应 section |
|---|---|
| `student_instruction` | 学生须知 |
| `history_taking` | 问诊（AI 标准化病人） |
| `case_presentation` | 病例汇报 |
| `structured_questions` | 结构化问答 |
| `scoring` | 评分与反馈 |

schema 会对未知 key 报错（`ValidationError`）。

## `patient_information` ↔ 需求 §9.2 PatientInformation

| JSON 字段 | 说明 | 必填 |
|---|---|---|
| `name` | 病人代码（虚拟病例使用化名） | 是 |
| `age` | 年龄，0–120 | 是 |
| `gender` | 性别 | 是 |
| `occupation` | 职业 | 否 |
| `ethnicity` | 族裔 | 否 |
| `patient_language` | 病人语言 | 否 |
| `chief_complaint` | 主诉 | 是 |
| `history_of_present_illness` | 现病史 | 是 |
| `review_of_systems` | 系统回顾（system → findings） | 否 |
| `past_medical_history` | 既往史列表 | 否 |
| `past_surgical_history` | 手术/创伤史 | 否 |
| `medications` | 用药列表 | 否 |
| `allergies` | 过敏列表 | 否 |
| `family_history` | 家族史 | 否 |
| `personal_social_history` | 个人与社会史（key → value） | 否 |
| `sexual_history` | 性史 | 否 |
| `obgyn_history` | 妇产科史 | 否 |
| `opening_statement` | SP 开场白 | 是 |
| `affect_style` | 情绪/表达风格 | 否 |
| `ice` | Ideas/Concerns/Expectations | 否 |
| `disclosure_rules` | SP 披露规则 | 否 |
| `qa_triggers` | 关键词触发问答 | 否 |
| `default_negative_response` | 未配置内容时的默认否定回答 | 否 |

## `examiner_pack` ↔ 需求 §9.3 ExaminerPack

| JSON 字段 | 说明 | 必填 |
|---|---|---|
| `case_summary` | 病例摘要 | 是 |
| `working_diagnosis` | 最可能诊断 | 是 |
| `differentials` | 鉴别诊断列表 | 否 |
| `structured_questions` | 结构化问题数组（≥1 条） | 是 |
| `suggested_answers` | 参考答案数组 | 否 |
| `physical_exam_release` | 体格检查结果释放项 | 否 |
| `investigation_release` | 辅助检查结果释放项 | 否 |
| `scoring_rubric` | 评分 rubric 或 `null` | 否 |

### `structured_questions[]`

| 字段 | 说明 |
|---|---|
| `id` | 问题 ID，如 `sq-1`（`suggested_answers[].question_id` 引用它） |
| `order` | 顺序，≥1 |
| `question` | 问题文本 |
| `language` | `en` \| `zh` |
| `reveal_items` | 该题作答后应释放的检查项 `item_id` 列表（见下） |

`reveal_items` 语义：值必须对应 `physical_exam_release` 或
`investigation_release` 中某个条目的 `item_id`。学生请求并命中释放项后，
结果固定展示（feat-007 使用）；未配置的请求显示 "not provided"。
phase 1 只入库，不在本期实现释放逻辑。

### `physical_exam_release[]` / `investigation_release[]`

统一结构：`{ "item_id": string, "name": string, "result": string, "reference_range": string | null }`

### `scoring_rubric`

`{ "max_score": int (>0), "criteria": [{id, label, description, weight}] }`。
**rubric 可缺省**：缺省（`null`/省略）时该病例不提供 AI 参考评分
（feat-008 会明确拒绝评分）。

## `review_record` ↔ 需求 §9.4 CaseReviewRecord

| JSON 字段 | 说明 | 必填 |
|---|---|---|
| `review_status` | 审核状态文本 | 是 |
| `reviewer_name` | 审核人 | 否 |
| `review_comment` | 审核意见 | 否 |
| `reviewed_at` | 审核时间（ISO-8601） | 否 |
| `published_at` | 发布时间（ISO-8601） | 否 |

## 使用方式

病例 JSON 放在 `backend/cases/*.json`，由种子脚本读取并校验：

```bash
cd backend && uv run python scripts/seed_cases.py
```

校验入口为 `cases.schema.CaseFile.model_validate(payload)`：缺失必填字段、
非法枚举、未知 section key、空结构化问题列表等都会被拒绝。
