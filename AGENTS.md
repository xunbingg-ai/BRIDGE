# AGENTS.md

OSCE 学生端训练平台：面向医学生的 OSCE 问诊训练网站。前端 Nuxt 4 + Pinia + Tailwind CSS（`frontend/`），后端 Flask + SQLite + JWT + OpenAI 兼容大模型（`backend/`）。AI 病人/考官/判卷走 DeepSeek V4 Flash（环境变量注入，未配置时自动降级为内置 Mock）。

## 启动流程 / Startup Workflow（Before writing code）

1. **确认工作目录**：`pwd`（应为仓库根 `/mnt/d/BRIDGE`）
2. **完整阅读本文件**
3. **阅读项目说明**：`README.md`
4. **运行 `bash init.sh`** 验证环境健康（后端依赖 + 前端构建均可通过）
5. **阅读 `feature_list.json`** 了解当前功能/状态
6. **查看最近提交**：`git log --oneline -5`

若基线验证失败，先修复它，再处理新需求。

## 工作规则

- **一次只做一个 feature（One feature at a time）**：从 `feature_list.json` 里选一个未完成项
- **必须验证**：未跑验证命令不得宣称完成
- **更新工件**：结束会话前更新 `progress.md` 和 `feature_list.json`
- **控制范围 / Stay in scope**：不要改动与当前 feature 无关的文件
- **保持干净**：下一会话必须能直接 `bash init.sh` 跑通

## 必需工件

- `feature_list.json` — 功能状态表（事实来源）
- `progress.md` — 会话连续性日志
- `init.sh` — 标准启动与验证路径
- `session-handoff.md` — 会话交接文档（较大改动/多会话时）

## 端到端验证门禁（Evaluator Gate）

**任何功能/改动在交接（标记 done / 合并 / 提交）前，必须通过独立上下文的 EVALUATOR 子代理做端到端验证。**

- **谁验证**：一个**独立的、全新上下文的 evaluator 子代理**（不与开发者/开发子代理共享上下文），只做验证、不做实现。
- **怎么验证**：运行 Playwright 端到端测试，覆盖本次改动的**完整用户流程**（页面渲染、登录、关键交互、API 链路、导航），确认全流程干净、无 bug。
- **怎么跑**：`cd frontend && bash e2e.sh`（等价 `pnpm e2e`）。e2e 由 `frontend/playwright.config.ts` 自动拉起后端(:5000)与前端(:3000)（已运行则复用）。
- **门禁**：**任何用例失败即视为未完成，不得交接**。开发者不得用自己的实现结果替代 evaluator 的验证。
- **环境依赖**：`@playwright/test` 已是前端 devDependency；Chromium 已装于 `~/.cache/ms-playwright`（跨会话可用）。测试用全量 Chromium（`channel: 'chromium'`）。e2e 脚本已绕过环境代理对 localhost 的干扰。

## 完成定义 / Definition of Done（DoD）

一个 feature 只有在**全部**满足时才视为完成：

- [ ] 目标行为已实现
- [ ] 必需验证已实际运行（构建 / 类型检查 / 接口测试）
- [ ] **独立 evaluator 子代理已运行 `cd frontend && bash e2e.sh` 且全部通过**（见「端到端验证门禁」）
- [ ] 证据已记录在 `feature_list.json` 或 `progress.md`
- [ ] 仓库仍可从标准启动路径重启（`bash init.sh` 通过）

## 会话结束 / End of Session

结束会话前：

1. 更新 `progress.md` 记录当前状态
2. 更新 `feature_list.json` 更新功能状态
3. 记录未解决的风险/阻塞项
4. 工作处于安全状态时用描述性 message 提交
5. 让仓库保持在 `bash init.sh` 可直接跑通的状态

## 验证命令

```bash
# 完整验证（推荐）
bash init.sh
```

必要检查：
- 后端：`cd backend && ./.venv/bin/python -c "import app"`（依赖/入口可 import）
- 数据库：`backend/osce.db` 存在且含 12 个内置病例 + 新增病例
- 前端：`cd frontend && pnpm install && pnpm build`（Nuxt 构建通过）
- 端到端：`cd frontend && bash e2e.sh`（Playwright：自动拉起前后端并跑冒烟/回归用例，见「端到端验证门禁」）

## 升级（Escalation）

- **架构决策**：先查项目文档（`docs/`、README），否则问用户
- **需求不明确**：查产品/需求文档，否则问用户
- **反复测试失败**：更新 `progress.md`，交给人工复核
- **范围模糊**：重读 `feature_list.json` 的完成定义
