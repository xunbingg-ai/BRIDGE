# Codex 多代理 v2 子代理任务投递不稳定 — 根因调查（2026-08-18）

## TL;DR

子代理"收不到任务 / 行为漂移"**不是 deepseek-v4-flash 模型的问题，而是 Codex CLI 多代理 v2（MultiAgentV2）的已知缺陷**：父→子的任务正文被放进私有 `agent_message` 响应项的 `encrypted_content` 字段（明文 `content` 为空），而使用自定义非 OpenAI provider（本项目为 DeepSeek，`wire_api = "responses"`）时该字段被丢弃/不可解码，子代理因此只收到空 Payload，只能从继承的历史上下文里"猜"任务。子→父（FINAL_ANSWER）方向是明文，工作正常。

## 现象（本 session 实测）

- `fork_turns="none"` 派发：子代理回复"没有收到任务"（task1_llm_client、delivery 测试代理）。
- `fork_turns="all"` 派发：部分代理能完成（Task 1/2/3 实现），部分是靠共享文件系统找到简报+继承上下文推断任务；另一些被继承历史里**更新的用户消息**劫持，做出与任务无关的行为（转发指令、重跑 smoke、以控制器口吻汇报流水线），甚至自行再派子代理（其孙代理同样收不到任务）。
- 派发提示里的"禁止派子代理"等指令无法生效——因为消息根本没送达。

## 本地证据

1. **配置**：`C:\Users\asus\.codex\config.toml` → `model = "deepseek-v4-flash"`、`model_provider = "deepseek"`、`[model_providers.deepseek] base_url = "https://api.deepseek.com/"`、`wire_api = "responses"`；`codex-cli 0.147.0`（npm 安装）。
2. **日志库** `C:\Users\asus\.codex\logs_2.sqlite`：共 27 条 `InterAgentCommunication` 提交记录满足 `content: ""` 且 `encrypted_content: Some(...)`（父→子方向）；样本如 `author: AgentPath("/root"), recipient: AgentPath("/root/task4_impl"), content: "", encrypted_content: Some("You are implementing Task 4: ...")`。
3. **子线程 rollout JSONL**（`~/.codex/sessions/2026/08/18/*.jsonl`）：每个子代理的 NEW_TASK 信封都是 `"Message Type: NEW_TASK\nTask name: ...\nSender: /root\nPayload:\n"`（明文 Payload 为空），完整任务正文只出现在同一条 `response_item` 的 `encrypted_content` 里——成功与失败的代理无一例外。

## 根因（GitHub 证据）

- **#36493**（2026-07-31，环境与本机几乎完全一致：Windows、Asia/Shanghai、自定义 DeepSeek provider、deepseek-v4-flash、Codex Desktop 引擎 0.146.0-alpha.9.2）：子代理 NEW_TASK 信封 Payload 为空；`InterAgentCommunication` 的 `content` 为空、正文在 `encrypted_content`；仅父→子方向受影响。该 issue 还给出了根因日志与 `state_5.sqlite` 中 `first_user_message` 的错误播种证据（fork=none 为空串、fork=1 取父线程最近用户消息、fork=all 取父线程首条用户消息）。
- **#36586**（2026-08-01）："Subagent task payload invisible to custom non-OpenAI providers (DeepSeek): encrypted_content block dropped with multi_agent_version v2" —— 自定义 provider 下 `encrypted_content` 块被丢弃。
- **#36321**、**#35932**、**#36387**：子代理收到空任务载荷（multi-agent v2 / 自定义 provider 路径）。
- **#24150**：`fork_context:true` 子代理不执行委派任务、继续父线程工作，甚至自行再派子代理（与我们的"漂移"完全吻合）。
- **#25458**：`fork_turns="none"` 时任务以 assistant/commentary 信封形式出现而非 user/task 消息。
- **#26130**：并行派发时子代理可能收到兄弟代理的信封。
- **#20077**：model/reasoning 覆盖要求 `fork_turns="none"`，缺省即 `"all"`（全量上下文）。

官方子代理功能文档：<https://developers.openai.com/codex/subagents>（本次抓取返回 403，内容未核实；bug 追踪以 GitHub issues 为准）。

## 是模型问题还是 CLI 问题？

**CLI 问题，与模型无关。** 证据：

- 所有派发的信封在投递层就已丢失明文 Payload（本地 27 条日志 + 子线程 JSONL），模型只看到空消息，任何模型都无法执行不存在的指令。
- 社区修复项目（见下）一致指出 `agent_message` / `encrypted_content` 是 Codex 私有协议假设，第三方（DeepSeek）provider 无法消费；与消息语言、fork_turns、模型选择无关。
- 为什么 Claude Code 的子代理"稳定"：两者是不同的产品与不同的消息通道实现；Claude Code 的委派消息走明文用户消息，不存在这套加密/明文分离的私有协议。故无同类已知缺陷。

## 解决方案

### 短期（本 session 适用）

- **不再依赖子代理任务投递**：控制器内联执行（TDD：先写失败测试 → 实现 → 提交 → 控制器审查）。零新工具、确定性最高。成功的那几个子代理本质是"猜对"了任务，不可依赖。

### 中期（若仍想用子代理）

- 社区修复（本地、自选其一，均属第三方补丁，需用户确认后再装）：
  - `hairyf/codex-deepseek-subagent-proxy`：本地转发代理，把 `agent_message` 转成普通 `user message` 修复 DeepSeek/非 OpenAI Responses provider 的任务投递。
  - `CCanxue/codex-deepseek-subagent-fix`：本地补丁（核心投递层）。
  - `nFr3axp1/codex-multi-agent-fixed`：同类多 Agent 修复工具。
- 或者等待 Codex 官方修复（给 #36493 / #36586 / #36321 加星/评论，关注新版本 release notes）；当前 0.147.0 仍存在该问题。

## 参考

- GitHub issues：openai/codex#36493、#36586、#36321、#35932、#36387、#24150、#25458、#26130、#20077
- 社区修复：<https://github.com/hairyf/codex-deepseek-subagent-proxy>、<https://github.com/CCanxue/codex-deepseek-subagent-fix>、<https://github.com/nFr3axp1/codex-multi-agent-fixed>
- 官方文档：<https://developers.openai.com/codex/subagents>（403 未取到正文）
