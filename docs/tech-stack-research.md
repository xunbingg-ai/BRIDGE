# feat-001 技术栈与骨架 —— 网络调研报告（2026-08-18）

## 1. 同类平台调研（我们不是在做没人做过的事）

| 平台 | 形态 | 可借鉴点 |
|---|---|---|
| MedSimAI（Weill Cornell，2025 试点） | 文本 + 语音虚拟病人，医学生练习问诊 | **双模型架构**：一个 LLM 按医生写的脚本扮演病人，另一个 LLM 用 OSCE 评分量表（MIRS）实时评估并给反馈。与 BRIDGE 的"AI 病人 + AI 评分"完全一致 |
| Geeky Medics SimChat（2026） | 文本/语音/视频虚拟病人 | 从现有病例脚本/OSCE 评分表生成场景；即时结构化反馈；场景库标签管理；班级完成度分析。佐证病例脚本驱动 + 结构化反馈 + 教师统计是成熟产品形态 |
| Monash MOVE（药学 OSCE） | 在线 20 个案例 + 虚拟病人 | 首期案例库规模参考：20 个以内足够；学生反馈积极，适合课外自主练习 |
| Cortex（BMC Medical Education 2026） | 自研语音 Web 应用，GPT-4o，双 prompt 架构 | 说明医学院小团队自研此类系统是可行路径 |
| medkit-app（GitHub 个人项目） | 浏览器端 AI 病人模拟器，OSCE 模式 | 开源参考实现，可看 UI 和交互思路 |

**结论**：BRIDGE 首期（文本问诊 + 病例汇报 + 结构化问答 + 检查揭示 + AI 评分）在同类产品中是常见形态，没有冷门技术难点。技术上最核心的参考是 MedSimAI 的"病人角色与评分角色分离"。

## 2. DeepSeek V4 Flash（0731）API 事实

- 模型 ID：`deepseek-v4-flash`（现指向 0731 正式版，Preview 代码无需改动）；官方 base URL：`https://api.deepseek.com`。
- **OpenAI SDK 兼容**：Python/Node.js 直接改 `base_url` + `api_key` 即可，无需专门 SDK。
- 原生支持 OpenAI **Responses API**，官方适配 Codex。
- 支持 **streaming（SSE）**、function calling、JSON 输出。
- **thinking 模式默认开启**，可用 `thinking` 参数关闭；开启时 `temperature`/`top_p` 无效，`reasoning_effort` 可调。
- 公开测试版价格：输入 $0.14/百万 token（缓存命中 $0.0028）、输出 $0.28/百万 token；上下文 1M token；最大输出 384K；并发上限 2500。
- API key 在 DeepSeek Platform 创建，用环境变量 `DEEPSEEK_API_KEY` 保存，**不写进代码**。
- 官网 changelog 确认：0731 仅做了再训练，架构尺寸不变；官方声明该版本为 Codex 专门适配。

## 3. 技术栈提案（待 grill 访谈确认）

### 方案 A —— 推荐：FastAPI + React（TypeScript）+ SQLite→PostgreSQL
- 后端：Python 3.13 + FastAPI + Uvicorn（原生 WebSocket，适合流式聊天）+ SQLAlchemy + Alembic 迁移
- 前端：React + TypeScript + Vite（SPA）
- AI：官方 `openai` Python SDK 直连 DeepSeek（`base_url="https://api.deepseek.com"`），**不引入 LangChain**（第一阶段保持最小）
- 数据库：开发用 SQLite，上线换 PostgreSQL
- 理由：这是开源社区 AI 聊天应用最主流的组合，参考项目最多（FastAPI + React AI chatbot 模板随处可见）；DeepSeek 官方支持 OpenAI SDK；聊天式交互用 SPA 体验最好
- 缺点：前后端两种语言

### 方案 B —— 最简：全 Python（FastAPI + Jinja2 + htmx + SQLite）
- 只有一种语言，医学生维护负担最小；多步骤考站用服务端渲染 + 少量 htmx 也能做
- 缺点：聊天/多面板交互（结果固定显示在右侧等）写起来不如 SPA 流畅，复杂页面会较难维护

### 方案 C —— 全 TypeScript（Next.js + Prisma + SQLite）
- 单一 JS 生态；但评分状态机、检查匹配这些核心逻辑用 JS 写，对非工程师更不友好；DeepSeek 集成示例也少

**倾向：方案 A；若 E1 回答"完全不想碰 JavaScript"，改选方案 B。** 评分和考站状态机一律放后端，前端只负责展示。

## 4. 骨架草案（方案 A）

```
D:\BRIDGE
├── backend/                 # FastAPI（uv 管理依赖）
│   ├── app/
│   │   ├── api/             # auth, cases, stations, chat, scoring 路由
│   │   ├── models/          # User, Case, PatientInformation, Question, Investigation, PracticeSession, Answer...
│   │   ├── services/        # SP 对话、检查请求匹配、评分
│   │   ├── prompts/         # 病人角色 prompt、评分 rubric prompt（放文件便于迭代）
│   │   └── core/            # 配置（读 DEEPSEEK_API_KEY 等环境变量）
│   ├── alembic/             # 数据库迁移
│   └── tests/
├── frontend/                # React + Vite + TypeScript
│   └── src/
│       ├── pages/           # 登录、病例列表、CCE 考站各 section
│       ├── components/      # 聊天窗、检查结果面板、评分反馈面板
│       └── api/             # 后端调用封装
├── docs/                    # 需求、调研、决策文档
├── docker-compose.yml       # 上线部署（可选）
├── AGENTS.md / feature_list.json / progress.md / init.sh   # harness（已有）
└── init.sh                  # 更新为真实验证命令（pytest + frontend build/typecheck）
```

## 5. 风险与待定

- DeepSeek API key 尚未注册（等用户注册后放环境变量）
- 部署目标（A2）、学生规模（A1）、账号方式（C1）、界面语言（B2）待确认
- 需求文档 §3.2 与 §9 的矛盾已解决：首期病例由开发者以结构化文件 + 种子脚本录入，不做网页表单
