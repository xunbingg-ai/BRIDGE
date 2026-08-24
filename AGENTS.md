# AGENTS.md

OSCE 学生端训练平台：面向医学生的 OSCE 问诊训练网站。前端 Nuxt 4 + Pinia + Tailwind CSS（`frontend/`），后端 Flask + SQLite + JWT + OpenAI 兼容大模型（`backend/`）。AI 病人/考官/判卷走 DeepSeek V4 Flash（环境变量注入，未配置时自动降级为内置 Mock）。

## 启动流程（写代码前）

1. **确认工作目录**：`pwd`（应为仓库根 `/mnt/d/BRIDGE`）
2. **完整阅读本文件**
3. **阅读项目说明**：`README.md`
4. **运行 `bash init.sh`** 验证环境健康（后端依赖 + 前端构建均可通过）
5. **阅读 `feature_list.json`** 了解当前功能/状态
6. **查看最近提交**：`git log --oneline -5`

若基线验证失败，先修复它，再处理新需求。

## 工作规则

- **一次只做一个 feature**：从 `feature_list.json` 里选一个未完成项
- **必须验证**：未跑验证命令不得宣称完成
- **更新工件**：结束会话前更新 `progress.md` 和 `feature_list.json`
- **控制范围**：不要改动与当前 feature 无关的文件
- **保持干净**：下一会话必须能直接 `bash init.sh` 跑通

## 必需工件

- `feature_list.json` — 功能状态表（事实来源）
- `progress.md` — 会话连续性日志
- `init.sh` — 标准启动与验证路径
- `session-handoff.md` — 会话交接文档（较大改动/多会话时）

## 完成定义（DoD）

一个 feature 只有在**全部**满足时才视为完成：

- [ ] 目标行为已实现
- [ ] 必需验证已实际运行（构建 / 类型检查 / 接口测试）
- [ ] 证据已记录在 `feature_list.json` 或 `progress.md`
- [ ] 仓库仍可从标准启动路径重启（`bash init.sh` 通过）

## 会话结束

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

## 升级（Escalation）

- **架构决策**：先查项目文档（`docs/`、README），否则问用户
- **需求不明确**：查产品/需求文档，否则问用户
- **反复测试失败**：更新 `progress.md`，交给人工复核
- **范围模糊**：重读 `feature_list.json` 的完成定义
