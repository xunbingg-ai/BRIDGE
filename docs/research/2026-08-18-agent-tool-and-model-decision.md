# Codex / dsh / ChatGPT Plus 开发工具与模型选型调研（2026-08-18）

## TL;DR

- **DeepSeek Harness（dsh 0.1.0-rc.6）不推荐作为本 session 主力开发环境**：v0.1 预览版，Windows 上问题成堆（MSYS2 bash 崩溃、热更新缓存、UTF-16 中文路径选择器 bug、超长会话 10 秒级延迟、未审批写入工作区外），官方关闭 GitHub Issues；官方 Terminal Bench 2.1 的 87.9 与第三方 Vals Terminus 2 的 54.68 相差 33.22 分。"极简模式 = V4-Pro 训练原生环境"解释了分数差，但社区已报告 anchored-standard 高分**无法稳定复现**——用户的"后训练过拟合"直觉基本成立（更精确：接口依赖 + 入口窄 + 复现不稳定）。
- **deepseek-v4-flash-0731 vs GPT-5.6 Luna（Together DeepSWE 官方实测）**：Luna 质量全面领先（pass@1 67.2% vs 53.3%；7/8 域、5/5 语言；Python 49→65、JS 35→60），成本约 6 倍（$0.61 vs $0.10/rollout），且 Luna 失败时更易破坏既有测试（15% vs 9%）。DeepSeek 先跑、测试门失败升 Luna 的级联方案达 78.9%、每任务 $0.385，比 Luna 单独用更准更便宜。
- **对 BRIDGE 的意义**：本项目是 FastAPI + React 常规 CRUD + 流程编排，属于 Flash 的舒适区（query/config 域 Flash 反而领先 78 vs 70）；Python 49 偏弱是主要风险点，用"测试门 + 控制器逐任务审查"兜底即可。
- **ChatGPT Plus**：Luna 配额日常够用（2026-07 OpenAI 还临时取消了 5 小时限额），Sol 10–100/5h 确实偏紧（用户判断正确）。附加收益：OpenAI 原生模型下 Codex 子代理投递 bug 消失。可买作困难任务的第二意见，非本 session 必需。
- **推荐**：本 session 继续 Codex CLI + deepseek-v4-flash-0731，控制器内联执行（不依赖子代理）；不迁移 dsh；Plus 可选买；以后若想恢复子代理，把 `~/.codex/models.json` 的 DeepSeek 条目 `multi_agent_version` 改为 `"v1"` 是已验证的最优 workaround。

## 背景

用户在是否更换开发工具链之间纠结：

1. **DeepSeek Harness（dsh）**：官方预览版，网上口碑两极；社区有人声称"极简模式 + Linux/macOS + V4-Pro-0813"可接近 Fable 水平，但用户怀疑这是后训练过拟合，且认为网上测评多为 toy demo（网页/游戏），不能代表真实开发与科研能力。
2. **ChatGPT Plus**：担心 5.6 Sol 配额不够；Luna 与 deepseek-v4-flash-0731 孰强孰弱、谁更靠谱未知。

本文档汇总社区、GitHub、官方博客等来源的证据，给出选型建议。子代理投递 bug 的根因见 `2026-08-18-codex-subagent-instability.md`。

## 一、DeepSeek Harness 核查

### 官方口径 vs 第三方：33 分差距

- 官方：V4-Pro-0813 在 Terminal Bench 2.1 拿 87.9（距 Fable 5 差 0.1）、DeepSWE 62.7、Cybergym 83.3。官方公告注明公开基准用 **dsh Minimal 模式**（max 档、topp=0.95、temperature=1.0），并声明"其他框架下结果可能略有不同"。
- 第三方 Vals（自研 Terminus 2 harness）三轮实测同一模型：平均 54.68，52 个模型中排第 33，hard tasks 仅 28.89 → 差距 33.22 分。
- 机制解释：Minimal 模式 = 4KB 系统提示词（"You are a helpful software engineer assistant."）+ 仅 `bash`/`str_replace_editor` 两个工具 + 禁用上下文注入/压缩——正是 V4-Pro RL 训练时的原生接口。社区在 dsh 内部实验：Minimal+max 连跑 99/96，切 Standard（25 工具）掉到 91，PTC 92。
- 关键反转证据：社区"anchored-standard"两阶段预设（首轮只给 Minimal 两工具，第一次工具调用后放开全部 25 工具）曾在 Windows 原生跑出 98/99，与 Fable 5 / Opus 5 / Sol 同档——但 **GitHub 上已有开发者报告同条件下无法稳定复现**；V4-Pro 还存在 "Let me" / "The user wants me" / "we" 三种推理风格，最强策略的触发入口很窄。

### Windows 实测问题（本机 + 社区）

- 本机 dsh 0.1.0-rc.6（默认 V4-Pro / reasoning high）：MSYS2 bash 崩溃（exit 127）、热更新缓存失效、未审批写入工作区外、UI 状态滞后 50 分钟等问题（本 session 先前实测记录）。
- 社区：#2990 Windows spawn bash 启动即崩（MSYS2 "couldn't create signal pipe"，ENOENT 未捕获致整个 harness 崩溃）；rc.6 著名 bug——Windows 原生目录选择器 `readUtf16` 只查低字节，含 0x00 低字节的汉字路径（如"开""一"）选不中；Windows+pwsh 下 `unknown tool ""`；长会话 DOM 全内存导致 10 秒级延迟。
- 项目状态：0.1.0-rc.6 仍带 rc，官方明示会有破坏性变更，且已关闭 GitHub Issues（讨论区承接）。

### 小结

dsh 的价值是"V4-Pro 启动钥匙"的研究价值，不是稳定开发环境。用户的"后训练过拟合"直觉基本成立，更精确地说是：**V4-Pro 对 Minimal 模式的提示词/工具 schema 存在接口依赖，入口窄、跨环境复现不稳定；V4-Flash 跨 harness 反而稳定，但峰值低**。对需要可复现、可交接、Windows 原生可用的 BRIDGE 开发而言，dsh 当前不是合格的主力。

## 二、Luna vs deepseek-v4-flash-0731（Together DeepSWE 官方实测）

来源：Together AI 对全部 113 个 DeepSWE 任务、每模型 4 次尝试（共 900+ rollouts）的实测。

| 维度 | deepseek-v4-flash-0731 | GPT-5.6 Luna |
|---|---|---|
| pass@1 | 53.3% | **67.2%** |
| pass@2 | 70.1% | **81.6%** |
| pass@4 | 80.5% | **90.3%** |
| 成本 / rollout | **$0.10** | $0.61（约 6x） |
| 每 $100 解决数 | **532** | 110 |
| 失败时破坏既有测试 | **9%** | 15% |
| 中位耗时 / 步数 | 23 min / 148 steps | **16 min / 92 steps** |
| 域领先 | 1/8（query/config：78 vs 70） | **7/8** |
| 语言 | Python 49、JS 35、Rust 55、Go 62 | **Python 65、JS 60、Rust 60、Go 79** |

- 相似度：per-task 相关 0.50；并集 106/113（93.8%）；Luna 独解 15 个、Flash 独解 4 个；不存在 Flash 横扫而 Luna 全错的域。
- 级联（DeepSeek 先跑、测试门失败升 Luna）：78.9% 解决率、$0.385/任务——比 Luna 单独（67.2%、$0.61）更准且便宜约 37%，甚至超过完美 one-shot 路由（74.3%）。
- 失败画像：两者都以 near-miss 为主（69% vs 66%），但 Luna 更可能碰坏原本通过的测试（GPT 家族 15–20% 通病）——部署 Luna 必须接全量回归门。

### 对 BRIDGE 的意义

- Flash 的强项（query/config：SQL 构建、键集分页、配置解析、schema 驱动、约定跟随）恰好覆盖本项目：JSON case 文件 schema + Pydantic 强类型 + 常规 CRUD + 流程编排。
- Flash 的 Python 49 偏弱是主要风险点 → 用 TDD 测试门 + 控制器逐任务审查兜底；其失败时破坏既有测试仅 9%，回归风险反而低于 Luna。
- Luna 是理想的"困难任务/复核"升级路径，不是日常主力。

## 三、ChatGPT Plus 评估

- 配额：Luna 250–2000/5h，Sol 仅 10–100/5h——用户"Sol 不够用"的判断正确，Luna 日常够用。
- 时效性补充：2026-07-12 OpenAI 临时取消 Plus/Business/Pro 的 5 小时限额并多次重置额度（未公布结束时间）；当前实际比名义配额更宽松，但属临时措施，规划仍应按名义配额算。
- 附加收益：Codex 多代理 v2 的 `encrypted_content` 投递缺陷仅影响自定义非 OpenAI provider（见子代理根因文档）；用 OpenAI 原生模型后该 bug 消失。
- 结论：可买，作为困难任务第二意见 + 潜在子代理恢复选项；不是本 session 完成 feat-010/011 的必要条件。

## 四、结论与建议

1. **不迁移 dsh 作为主力**。可留作受控实验（评估 anchored-standard 首轮锚定对本项目场景是否有效），但完成本 session 不依赖它。
2. **继续 Codex CLI + deepseek-v4-flash-0731**，控制器内联执行剩余任务（TDD + 逐任务提交 + 控制器审查），用测试门覆盖 Flash 的 Python 弱项。
3. **Plus 可选买**：Luna 日常够用、Sol 偏紧的判断正确；买了可获得第二意见与子代理修复选项，不买也不阻塞。
4. **子代理恢复路径**（若用户坚持要子代理）：`~/.codex/models.json` 中 DeepSeek 条目 `multi_agent_version` 改 `"v1"`（issue #36586 验证过的 workaround）；或安装社区代理补丁（第三方代码，需另行确认）。
5. 本 session 推进顺序：Task 4（case JSON schema + 格式文档 + TDD 测试）→ Task 5（中文种子脚本 + GP-ChestPain-0001.json）→ Task 6（导入测试）→ Task 7/8/9（SP / 评分 / SSE）→ Task 10（状态文档 + 最终验证 + 提交）。

## 五、后续 session 主力组合选型（三选一）

用户待选：**dsh + deepseek-v4-flash-0731 / codex cli + gpt-5.6-luna / codex cli + deepseek-v4-flash-0731**。本节为 2026-08-18 补查证据。

### 关键新证据

1. **dsh 的"极简模式魔法"只对 V4-Pro 有效，对 Flash 无效**：社区实测 V4 Flash 在不同 harness 下分数稳定（90–95），切换到极简模式也无变化——dsh 对 Flash 没有 Pro 那种"启动钥匙"加成，只额外引入 harness 自身的复杂与不稳定。
2. **dsh 核心层存在 Flash 专属未修复 bug**（Discussion #725 / #161）：V4 Flash（或任何以多 SSE 分块返回工具调用续 delta 的模型）在流式模式下所有工具调用报 `unknown tool ""`；根因在 `packages/llm/llm-deepseek/src/translate.ts` 159–160 行——续 delta 中 id/name 为 null 时覆盖了首块值。官方关闭 Issue/PR 提交，用户需自行改源码 + `pnpm run build` 重启。社区已累计 173+ 真实痛点（含 Windows 中文路径截断、无成本统计、纯文本模型不能看图等）。
3. **dsh 的子代理能力全部来自社区第三方扩展**（dsh-team、dsh-forge `modsub`、dsh-background-agents、dsh-ai-solution-council），非核心功能，成熟度低且互相叠加不稳定。
4. **Luna 在 Codex 里不是一等公民**：模型目录把 Luna 钉在 `multi_agent_version: "v1"`；2026-08-16 开发者报告 OpenAI 把 GPT-5.6 Luna 移出 V2 `spawn_agent` 目标（issue #35097），V2 委派只支持 Sol/Terra；sol-advisor 作者实测"Luna 在子代理角色表现差（疑似未针对 v2 多代理协议后训练）"，Diego Haz 独立撞到同一堵墙。社区共识：**给 Luna 独立顶层线程**，由 Sol 编排、Sol 复核，而非放进子代理图。同日 OpenAI 社区帖子标题称"Sol 现在可以委派 Luna"——两种说法并存，该区域正快速变动，workaround 均为 V1 回退或"delegate new thread"措辞。
5. **Composio 实测（8 个 harness × 30 个复杂多步任务，240 runs）**：V4 Flash 真实 agent 任务完成率仅 53.8%（129/240），且同模型在不同 harness 下结果差异巨大（仅 6/30 工作流被所有 harness 完整完成）——对 Flash 而言 harness 几乎决定成败。
6. **DeepSeek 宣布涨价（VentureBeat，2026-08-15）**：Flash 峰值 44¢/M in、$1.32/M out（涨幅 57–371%），低谷（17/24 小时）22¢/66¢；Pro 峰值 132¢/396¢。涨价后 Flash 与 Luna 的输出单价在峰值档几乎持平（$1.32 vs $1.20），低谷档仍约为一半。分析师共识：Flash 定位"高频量大的 worker / 批处理"，困难任务应放别处；成本单位应看"每成功完成工作流"，而非每 token。

### 三组合对比

| 维度 | dsh + v4-flash-0731 | codex cli + gpt-5.6-luna | codex cli + v4-flash-0731（现状） |
|---|---|---|---|
| 子代理稳定性 | 核心无子代理，靠第三方扩展，未经验证 | 原生 OpenAI 路径无 encrypted_content bug；但 Luna 被移出 V2 spawn_agent（V1 / 独立线程 workaround） | v2 投递 bug 必现；v1 workaround 已验证可用 |
| Windows 可用性 | 差（MSYS2 崩溃、中文路径 bug、流式工具 bug 需自改源码） | 好（Codex 原生） | 好（Codex 原生） |
| 编码质量（Python/JS） | Flash 级别（DeepSWE 53.3%；Python 49 / JS 35） | Luna 级别（DeepSWE 67.2%；Python 65 / JS 60，更快） | Flash 级别 |
| 成本 | $0.10/rollout；涨价后优势缩小，峰值输出价 ≈ Luna | $0.61/rollout；Plus 订阅 Luna 配额日常够、Sol 紧 | $0.10/rollout；同左涨价风险 |
| 失败画像 | Flash：破坏既有测试少（9%） | Luna：破坏既有测试多（15%），必须接回归门 | Flash：9% |
| 主要风险 | 核心 bug + 生态不成熟 + 对 Flash 无极简加成 | Luna 指令漂移、TTFT 长（max 约 136s）、上下文烧得快；复杂任务需 Sol 复核（Sol 配额紧） | Flash Python/JS 弱；子代理 bug 需 workaround；涨价 |

### 建议（后续 session）

1. **若愿意买 Plus：codex cli + gpt-5.6-luna（Sol/Luna 分层）**。这是三者中唯一能同时拿到"原生子代理投递正常 + 高质量编码"的组合；Luna 的甜区（边界清楚、可验证、TDD 任务简报）与 BRIDGE 逐任务开发方式匹配。正确姿势是社区验证过的分层：Sol 主线程拆任务/定架构/终审，Luna Max 独立线程做有界实现，fresh Sol 复核——不要把 Luna 当全能主力（激活参数小，复杂任务易漂移返工，Diego Haz 实测返工可吞掉全部省下的钱）。
2. **不买 Plus 时：继续 codex cli + deepseek-v4-flash-0731**。成本低、失败破坏小（9%）、query/config 域适配本项目；子代理用 `multi_agent_version: "v1"` workaround 或继续内联执行；涨价后把批处理/重活排到低谷档（17/24 小时半价）。
3. **不建议 dsh + v4-flash-0731 作主力**：dsh 的极简加成只属于 V4-Pro，Flash 在 dsh 上既无加成又要吃核心流式 bug + Windows 不稳定 + 第三方子代理扩展，纯风险无收益。若想试 dsh，应配 V4-Pro 做受控实验且优先 Linux/macOS，不接 BRIDGE 日常开发。
4. **跨组合通用规则**：无论选哪个组合——接测试门/回归门、主线程逐 diff 审查、困难与模糊任务留给强模型（Sol/Luna/Terra/Pro）、机械任务交给便宜模型（Flash）、以"每成功完成工作流"核算成本。这正是本 session 已采用的内联 TDD + 逐任务提交 + 控制器审查模式，后续可平滑升级为"Sol 编排 + Luna worker + 测试门"。

## 参考链接

- Together AI: DeepSeek-V4 Flash 0731 vs GPT-5.6 Luna on DeepSWE（成本与编码能力实测）：<https://www.together.ai/blog/deepseek-v4-flash-0731-vs-gpt-5-6-luna-on-deepswe-cost-and-coding>
- jdon: DeepSeek V4 Pro 换壳跌 33 分，Harness 极简模式才是真钥匙（机制分析 + anchored-standard 复现不稳定）：<https://www.jdon.com/94051-deepseek-v4-pro-harness-dismatch.html>
- deepseek-ai/deepseek-harness Discussion #2990：Windows spawn bash ENOENT / MSYS2 signal pipe：<https://github.com/deepseek-ai/deepseek-harness/discussions/2990>
- dsh-handbook discussion-mining：rc.6 Windows 系列 bug（readUtf16 中文路径、unknown tool ""、长会话延迟）：<https://github.com/Electricitysheep/dsh-handbook/blob/main/docs/research/discussion-mining.md>
- IT之家：OpenAI 优化 GPT-5.6 Sol 并临时取消 5 小时限额：<https://m.ithome.com/html/975974.htm>
- 凤凰科技：同一事件的补充报道：<https://tech.ifeng.com/c/8uj5kWmA5MJ>
- deepseek-ai/deepseek-harness Discussion #725 / #161：V4 Flash 流式工具调用 `unknown tool ""` 根因与自修方案：<https://github.com/deepseek-ai/deepseek-harness/discussions/725>
- explainx.ai：Codex Multi-Agent V2 委派变化（Luna 被移出 V2 spawn_agent，issue #35097）：<https://explainx.ai/blog/codex-multi-agent-v2-delegation-gpt-5-5-restricted-models-august-2026>
- OrcaRouter：GPT-5.6 Luna Max in Codex 实战（TTFT、上下文燃烧、独立线程模式、五问交接包）：<https://www.orcarouter.ai/blog/gpt-5-6-luna-max-codex-playbook>
- 智差：Codex 新分工——Sol 当包工头、Luna Max 做边界清楚的体力活：<https://www.zhichai.top/archives/13699>
- VentureBeat：V4 Flash 真实 agent 任务翻车 + DeepSeek 涨价（57–371%）：<https://venturebeat.com/orchestration/deepseeks-top-ranked-v4-flash-stumbles-on-real-agent-tasks-as-its-prices-surge>
- 阿里云开发者社区：极简模式实测——Flash 跨 harness 稳定、极简对 Flash 无加成：<https://developer.aliyun.com/article/1755989>
