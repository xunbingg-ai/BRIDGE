# 启动就绪清单（每次会话开始执行）

适用对象：任何新会话的 agent（Codex 等）。目标：5 分钟内确认环境健康、掌握当前状态、选定一个任务。本清单是 AGENTS.md 启动流程的可执行版本。

## 0. 环境确认

- [ ] 确认当前工作目录：`D:\BRIDGE`（WSL 内 `/mnt/d/BRIDGE`）
- [ ] 确认 WSL Ubuntu 2 可用：`wsl -l -v`
- [ ] 确认工具链：node ≥ 24、npm ≥ 11、uv ≥ 0.12、python ≥ 3.12（均在 WSL 内）

## 1. 读取上下文（按顺序）

- [ ] `AGENTS.md` — 工作规则、完成定义（Definition of Done）
- [ ] `CONTEXT.md` — 领域术语（说话用词必须一致）
- [ ] `README.md` 与 `docs/adr/` — 项目概览与已记录决策
- [ ] `feature_list.json` — 特性状态（唯一事实源）
- [ ] `progress.md` 与 `session-handoff.md` — 进度日志与上次交接
- [ ] `docs/TASK-BREAKDOWN.md` — 子任务分解与验收标准
- [ ] 需求权威：`BRIDGE - 首期需求文档.md`

## 2. 验证 checkpoint

- [ ] `git status --short` 为空；若非空，先提交或明确说明未提交内容
- [ ] `git log --oneline -3` 确认从干净的 checkpoint 开始
- [ ] 运行 `bash init.sh`（在 WSL 内）→ **必须全绿**：
  - 后端 `uv run pytest -q` 全部通过
  - 前端 `npm run typecheck` 干净
  - 前端 `npm run build` 成功

> 如果 init.sh 失败：先修复再开工，禁止带病开发。

## 3. 选定任务

- [ ] 从 `feature_list.json` 选**一个**未完成 feature（一次只做一个）
- [ ] 到 `docs/TASK-BREAKDOWN.md` 找到该 feature 的第一个未完成子任务
- [ ] 在 `progress.md` 记录本会话目标（Session ID、Active Feature）

## 4. 收尾（离开前必做）

- [ ] 更新 `feature_list.json`：状态 + 证据（命令和输出）
- [ ] 更新 `progress.md`：已完成、决策、文件、证据、风险
- [ ] 更新 `session-handoff.md`：当前目标、阻塞、下一步
- [ ] 运行 `bash init.sh` 全绿
- [ ] `git commit`，`git status --short` 为空，记录 checkpoint commit

## 故障处理

- **无 `DEEPSEEK_API_KEY`**：feat-011/005/008 的联调必须用 mock 客户端，禁止假装已联调。
- **需求歧义**：以需求文档为准；术语以 `CONTEXT.md` 为准；拿不准就记入 progress.md 风险区并询问用户。
- **真人病例**：入库前必须脱敏，病例内容禁止写入日志。
