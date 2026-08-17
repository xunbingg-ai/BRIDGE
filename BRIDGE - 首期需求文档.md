# 教学病例库平台需求确认文档

## 1. 文档目的

本文档用于和甲方最终确认首期开发范围。本文档只描述业务需求、流程规则和验收边界，不展开具体技术实现。

首期目标是交付一套可试用的 AI 标准化病人 CCE 练习系统，让学生无需真人结对，也能按考站流程完成问病史、病例汇报、结构化问答、结果揭示和 AI 参考评分。

## 2. 需求理解

本项目不是普通病例题库，也不是简单主观题答题系统。核心需求是把线下 PMGP的CC搬到线上：

1. 学生进入一个病例。
2. 系统展示学生任务说明和病人基本信息。
3. AI 扮演标准化病人，学生向 AI 问病史。
4. 学生完成病例汇报。
5. 学生回答结构化问题。Differential diagnosis - Physical Exam - Supplimentary tests (labs, imaging, etc) - Management
6. 学生提出体格检查或辅助检查需求后，系统按病例配置展示对应结果。
7. AI 根据 rubric给出练习参考分、反馈和参考答案。

首期重点是"把练习流程跑通"，用于教学反馈，不作为正式考试系统。

## 3. 首期范围

### 3.1 首期必须支持

- 学生账号登录。
- 教师账号登录。
- 学生查看可练习病例列表。
- 学生进入 OSCE station 练习。
- AI 标准化病人文字问诊。
- 病例汇报文字输入。
- 结构化问题逐题作答。
- 体格检查、辅助检查结果按学生请求匹配展示，补充信息按配置揭示。
- AI 根据评分标准给出练习参考分和反馈。
- 学生完成后查看参考答案、AI 评分和反馈。
- 教师查看基础练习完成情况。

### 3.2 首期暂不支持

- 语音输入、语音转写、AI 语音播放。
- 正式考试模式。
- 强制倒计时、铃声提醒、自动跳转。
- 虚拟人或视频形象。

- 线上病例审核流。
- 教师通过网页表单维护病例基础信息、病人脚本、检查项目、题目、结果揭示内容和 rubric。

- 校园统一身份认证。

- PDF、Word、普通文本等非结构化文件直接导入病例库。
- 批量 Excel 导入。
- AI 评分校准、模型微调、专门医学模型训练。
- 医院系统或真实医疗数据对接。
- 教师人工评分和人工覆盖 AI 分数。

## 4. Station 类型

首期学生端只开放 `CCE station`。

S1 History Taking 和 S4 Reasoning & Management 不作为首期独立入口，只作为 CCE station 内部流程的参考模板：

| 类型 | 首期定位 |
| --- | --- |
| CCE station | 首期学生实际练习入口 |
| S1 History Taking | 参考"问病史 + 病例汇报"流程和评分结构 |
| S4 Reasoning & Management | 参考"结构化问题 + 分阶段结果揭示"流程和评分结构 |

## 5. 练习模式规则

首期只做练习模式。

- 练习模式不限时。
- 学生只能按 section 顺序推进。
- 学生不能自由回看上一阶段。
- 学生中途退出后允许重新进入继续。
- 学生完成后可以看到本次练习反馈和参考答案。
- 练习分数只作为即时参考，不纳入学生整体表现统计。
- 学生侧不提供长期历史作答回顾。

后续考试模式再加入限时、抽题、正式成绩统计和考试记录。

## 6. CCE 练习流程

首期 CCE station 建议流程如下：     Follow-up-visit (patient consultation) - II期

1. `Student instruction`
   - 学生阅读病例开场信息、任务说明和流程说明。

2. `History taking`
   - 学生向 AI 病人问病史。
   - AI 只扮演病人，不主动给出诊断、答案或评分点。
   - 病人只根据病例脚本回答。

3. `Case presentation`
   - 学生输入病例汇报。
   - 汇报语言按病例要求配置。

4. `Structured questions`
   - 系统逐题展示结构化问题。
   - 学生逐题作答。
   - 特定题目提交后，系统可继续揭示对应的 provided information/results。

5. `Scoring and feedback`
   - AI 根据 rubric 给参考分。
   - 系统展示 AI 反馈、参考答案和教学解析。

低年级版本可以只完成 `History taking + Case presentation` 后结束。高年级版本完成完整 CCE 流程。

## 7. 语言规则

语言规则按每个 section 的病例要求配置。

- 如果某个 section 要求中文，学生输入和 AI 回复都应使用中文。
- 如果某个 section 要求英文，学生输入和 AI 回复都应使用英文。
- 不允许在同一个 section 中中英混合。
- 平台不把 CCE 固定为"中文问病史 + 英文汇报 + 英文结构化问题"，具体语言由病例配置决定。

## 8. 体格检查和辅助检查规则

首期采用"学生请求驱动"的检查结果展示方式，模拟真实门诊中医生开出检查项目，病人完成检查后带报告回诊。

规则如下：

1. 学生在回答结构化问题的过程中提出体格检查或辅助检查需求，例如"测血压""做心电图""查血"。
2. 系统识别检查名称，并在当前病例配置的检查项目库中匹配。
3. 如果病例已配置该检查结果，系统展示对应结果或报告。
4. 如果病例未配置该检查结果，系统提示该病例未提供此项结果，不让 AI 编造。
5. 已展示的结果固定显示在当前页面，方便学生后续作答查看。
6. 回答完所有结构化问题后可按病例配置揭示补充信息或标准报告，但不替代学生请求驱动的检查结果展示。
7. AI 不允许自由编造任何检查结果。

## 9. 病例数据内容（by 8.7定稿 + example case - Cecilia）

首期病例主要通过网页表单录入。系统应把患者姓名、性别、年龄、主诉、病人脚本、检查项目、结构化问题、参考答案、rubric 等字段拆成清晰输入项，教师逐项填写、保存，最后提交并发布。

后续可以扩展 Excel 或 JSON 导入，但导入文件必须按数据库需要的字段结构组织。PDF、Word、普通文本文件不作为病例入库格式。

每个正式可练习病例建议至少包含：

1. Case
- id
- title
- type: initial_visit | follow_up_visit
- systemTags
- difficulty
- languageAvailability
- learningObjectives
- studentInstructions
- status: draft | in_review | approved | published

2. PatientInformation
- name
- age
- gender
- occupation
- chief complaint
- history of present illness
- review of system
- past medical history
- personal & social history
  - Smoking/Alcohol/Diet/Occupation exposure/Travel/Contact history
- family history
- openingStatement
- affectStyle
- ice
- disclosureRules
- qaTriggers
- defaultNegativeResponse ?

3. ExaminerPack
- caseSummary
- workingDiagnosis
- differentials
- structuredQuestions
- suggestedAnswers
- physicalExamRelease
- investigationRelease
- scoringRubric

4. CaseReviewRecord
- caseId
- reviewStatus
- reviewerName
- reviewComment
- reviewedAt
- publishedAt

如果病例暂时没有 rubric，可以先用于流程练习，但不能输出正式 AI 分数。
