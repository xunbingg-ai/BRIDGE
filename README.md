# BRIDGE — AI 标准化病人 OSCE/CCE 教学病例库平台

面向医学生的 OSCE（客观结构化临床考试）训练网站。首期交付一套可试用的 AI 标准化病人 CCE 练习系统：学生无需真人结对，即可按考站流程完成问病史、病例汇报、结构化问答、结果揭示和 AI 参考评分（练习模式，非正式考试）。

## 源文档

- `BRIDGE - 首期需求文档.md` — 首期需求与验收边界（权威依据）
- `Case repository - Template(1).xlsx` — 病例录入模板
- `Example teaching case.md` — Cecilia 示例病例（GP-ChestPain-0001）
- `Building BRIDGE Between English-medium Medical Training and Chinese Clinical Practice...pdf` — 背景论文（签署版）

## 开发约定（harness）

- `AGENTS.md` — agent 工作规则：启动流程、工作规则、完成定义
- `feature_list.json` — 特性状态跟踪（唯一事实源）
- `progress.md` — 会话进度日志
- `init.sh` — 标准启动与验证入口
- `session-handoff.md` — 会话交接模板
- `docs/STARTUP-CHECKLIST.md` — 启动就绪清单（每次会话必读）
- `docs/TASK-BREAKDOWN.md` — 子任务分解与验收标准
- `docs/adr/` — 架构决策记录

规则：一次只做一个特性；完成前必须运行验证命令；证据写入状态文件；离开时保持仓库可从标准启动路径直接运行。

## 当前状态

首期范围：CCE station 练习模式。技术栈待定（见 `progress.md`，feat-001）。

## 开发环境（WSL）

开发命令统一在 WSL（Ubuntu 2）里运行，仓库位于 `D:\BRIDGE`（WSL 内路径 `/mnt/d/BRIDGE`），与线上 Linux 环境保持一致。

```bash
# 首次安装依赖
bash scripts/setup-dev.sh

# 完整验证（后端 pytest + 前端 typecheck + build）
bash init.sh

# 后端开发服务器
cd backend && uv run uvicorn app.main:app --reload

# 前端开发服务器
cd frontend && npm run dev
```

技术栈：FastAPI（Python）+ React + TypeScript + Vite + Tailwind v4 + shadcn/ui；开发用 SQLite，上线 PostgreSQL。决策记录见 `docs/adr/`。
