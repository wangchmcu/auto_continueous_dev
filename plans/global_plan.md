# Global Plan

## 定义

`global plan` 指整个长周期算法迭代上下文管理方案。它不是某一个版本，也不是单个 skill；它的目标是让 Codex agent 在长周期实验中能恢复状态、避免重复路线、保存证据、生成交接，并在 Codex CLI 会话内主动调用本地工具。

## 总体形态

最终形态是轻量本地编排系统加 Codex 入口能力。

- 轻量本地编排系统：`auto_iteration` 负责写 SQLite、记录 runs、记录 decisions、保存 logs、生成 summaries、生成 handoff。
- Codex 入口能力：Codex agent 在会话内知道何时调用 `auto-iter`，用户不需要退出 Codex CLI，也不需要每次手写绝对路径。

## 全局能力清单

### 1. 状态账本

- 记录 run、config、dataset、command、git commit、git branch。
- 记录 metrics 和 artifacts。
- 记录 run 状态：running、success、failed、aborted。
- 每个实验都有 `run_id`。

### 2. 日志和摘要

- 捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。
- 生成 `summary.md`。
- 生成 `logs/error_summary.md`。
- 默认读取 summary 和 error_summary；只有调查具体失败时才读原始日志。

### 3. 结论和路线控制

- 记录 active、rejected、superseded、open 状态的 decision。
- 每个 decision 必须有 evidence run IDs。
- 新路线前运行 route check。
- 阻止明显重复配置和 rejected/superseded 路线。
- 后续增强方法被替代、参数空间被部分否定、重开条件提示。

### 4. 交接和恢复

- 自动生成 `handoffs/latest_handoff.md`。
- handoff 指向 run summaries、decisions、plans，而不是粘贴完整原始日志。
- handoff 生成 `Current Baseline`（当前基线：当前被承认为继续开发起点的版本、方法、结果和证据入口）Markdown projection（从已有记录摘出的可读视图，不是新的事实源），只放主线入口和证据入口，不复制完整评估规则、产物来源或诊断详情。
- 新 Codex session 先读 handoff、global plan、version tracking、active plan；项目根目录存在 `AGENTS.md` 时才把它作为项目级 Codex 规则入口读取。
- 后续增加 handoff 完整性校验，检查关键字段缺失。

### 5. 原始输入目录

- 每个项目开发目录可以有 `raw_input/`，用于存放原始输入材料或老项目导入材料。
- `raw_input/` 只在两种情况下读取：初次开始项目；后续开发中明确需要到原始输入里检索缺失信息。
- 初次开始项目时，agent 应先用 `context index --include-raw-input` 检查是否存在原始材料；如果存在，只选择性读取相关章节，不整目录吞入。
- 正常迭代时应优先读取 `plans/`、`handoffs/`、`decisions/`、run summaries 和 SQLite 状态库。
- 理论上，工作 tracking 信息应该已经吸收并更新了 `raw_input/` 中的重要信息；如果二者冲突，默认以 tracking 信息为准，除非用户明确要求回到原始输入核对。
- 从 `raw_input/` 找到的新信息，必须沉淀回 `plans/`、`decisions/`、handoff 或 run summary，避免下次再次回查原始材料。
- 从 `raw_input/` 沉淀的信息必须标注 `raw_input_source`，避免和用户确认目标或 agent 推断混在一起。

### 6. Codex 入口能力

- 提供 Codex 入口 skill：告诉 agent 什么时候调用 `auto-iter doctor`、`auto-iter resume`、`auto-iter route check`、`auto-iter run exec`、`auto-iter decision add`、`auto-iter handoff generate`。
- AIT 命令在已初始化项目子目录中运行时，按最近的父级 `state/agent_state.db` 定位项目根目录；`run exec` 的命令从该项目根目录启动，实验需要子目录时由 `--command` 内部显式 `cd`。
- 提供短命令入口 `auto-iter`，避免每次手写源码 checkout 里的工具脚本路径。
- 安装和运行入口必须覆盖 Windows Codex app、WSL/Linux Codex CLI、macOS Codex app 三类环境；wrapper、Python 命令和文档不能写死某一个用户或系统路径。
- 安装器应优先使用当前操作系统和 shell 已认可的命令目录；如果没有合适目录，回落到用户目录并提示路径，不默认修改用户 shell 配置。
- `auto-iter handoff generate` 默认不输出 stdout，避免 Codex Stop hook 把普通文本当作 hook JSON 解析；需要人工调试时显式使用 `auto-iter handoff generate --print-path`，且不能依赖平台特定 shell 重定向。
- 提供安装管理入口：可安装、卸载并重新安装命令和 Codex skills，且卸载不删除项目状态。
- 提供更新入口 `auto-iter update`：更新已安装命令 wrapper 和 Codex skills，语义等价于保留项目状态的卸载再安装；默认不运行 `init`，避免在错误目录创建或污染项目状态。需要检查当前项目状态时显式使用 `--check-project`。
- 用户在 Codex CLI 中表达任务，agent 在同一个会话里调用命令；用户不需要退出 Codex CLI。
- 入口 skill 只负责流程触发和命令调用顺序；状态写入仍由 `auto_iteration` 完成。

### 7. 动态载入上下文

- 建立按标题索引的上下文读取方式：先读目录和摘要，需要时再读详细内容。
- handoff、decision、run summary、error summary 都应可被按需读取。
- 避免一次性把所有历史塞进上下文。

### 8. Topic Archive（按 topic 归档和按需载入）

- `default topic`（默认 topic：项目级默认恢复入口，兼容旧的 `active topic` 语义）用于新 session 的默认读取和单 topic 工作流。
- `topic_id` 是 topic 的事实绑定入口；多 Codex thread 并行工作时，写入命令应通过 `--topic-id` 或 `AUTO_ITER_TOPIC_ID` 绑定到指定 topic。
- 非默认 topic 可以保持打开状态并被显式读取、计划和交接，不应因为另一个 thread 工作而被强制切走。
- archive 内区分 `archived_open` 和 `archived_satisfied`。
- `archived_open` 表示已归档但问题仍打开，切回时默认继续工作。
- `archived_satisfied` 表示阶段性达到预期，不等于永久结束；切回时记录重开事件并恢复为 active。
- topic 事实记录在 SQLite，Markdown 投影写入 `topics/active_topic.md`、`topics/index.md`、`topics/<topic_id>/` 和兼容 archive 文件。
- 显式 topic 切换短句可直接触发 topic 命令；语义疑似切换时必须先问用户“是不是已经切入新的 topic 了？”。
- topic evidence link（topic 证据关联）把 topic 与相关 run、decision、artifact 建立可查询关联，避免恢复 topic 时逐个翻找历史。
- topic plan（topic 内计划：单个 topic 的目标、非目标、任务状态、验收、停止条件和升级条件）承担类似 Jira 的局部看板；global plan 只保留长期方向、模板、跨 topic 总览规则和升级规则。
- project board（项目 topic 总览：跨 topic 的 open、doing、blocked、done 摘要）承担类似 Jira 的全局看板，不把单个 topic 的细节塞进 global plan。

### 9. 自然语言接力入口

- 用户可以用自然语言短句触发固定流程，例如结束 session、恢复 session、查阅某个历史细节。
- Codex entry skill 负责把这些短句映射到 `auto-iter` 命令序列。
- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 等具体命令。

### 10. Auto It Self Improve（系统改进沉淀能力）

- `auto it self improve` 是固定触发短句和能力名，指 auto_iteration 的系统改进沉淀能力：用户和 agent 解决了一个具体使用问题后，agent 把这个问题抽象成通用能力改进，并更新到 auto_iteration 系统中。
- 这个能力不能自动触发，只能在用户明确点名 `auto it self improve` 或 `auto-it-self-improve` skill 名时触发。
- 输入是已解决的对话片段、相关文件改动、失败现象和最终处理方式；输出是对 auto_iteration 系统的通用改进建议或补丁。
- 改进落点由 agent 根据问题类型选择，例如 `AGENTS.md`、README、entry skill、workflow skill、CLI 命令、初始化模板、测试、plans 或 handoff 模板。
- 必须先抽象成通用规则，再写入系统；不得把具体项目名称、具体数据集、一次性参数、临时文件路径或用户当次私有场景直接写成系统规则。
- 每次执行都应说明“具体问题是什么”“抽象后的通用问题是什么”“为什么应该改这些文件”“哪些具体细节没有写入系统”。

### 11. Intent Checkpoint（意图检查点）

- Intent checkpoint（意图检查点）指：用户话语像是在进入计划、执行前、结果后或 session 结束阶段时，agent 先运行检查命令获取下一步清单。
- 该能力的目标是减少漏记计划、漏做 route check、漏写 decision、漏生成 handoff，而不是自动替代 agent 判断。
- `auto-iter intent check --text "<用户原话>"` 只输出检查清单；它不直接写 SQLite、不启动实验、不生成结论。
- Codex entry skill 负责在用户说“做个计划”“更新计划”“执行吧”“实施吧”“确定执行”“拿到结果了”“跑完数据了”“测试结束了”“结束当前 session”等相似短句时调用该命令。
- 检查结果必须继续落回现有明确流程：计划文件、`route check`、`run exec`、`decision add`、`handoff generate` 和 `handoff validate`。

### 12. 中途记录黑盒入口

- 中途记录黑盒入口指：用户在对话中只说“中途记录一下”“先保存当前状态”“做个阶段记录”等自然语言短句，agent 自动保存当前接力点。
- 这个入口和 session 结束使用相同的状态保存范围：检查当前计划、实验事实、结论和 handoff 是否需要更新，并生成可恢复的 handoff。
- 它和 session 结束的区别是：中途记录不表示当前 session 结束，不默认提交，不默认推送。
- `auto-iter checkpoint save --text "<用户原话>"` 是 agent 内部使用的命令；用户不需要记住它。
- 如果用户同时明确要求“提交”或“推送”，agent 才在 checkpoint 后执行对应 git 操作。

### 13. 低假设初始化和 bootstrap checkpoint

- `auto-iter init` 只创建状态结构和低假设 tracking 模板，不替目标项目发明业务 roadmap。
- 初始化模板必须区分 `user_confirmed`、`repo_observed`、`conversation_summary`、`agent_inferred` 和 `proposed_not_accepted`。
- 初始化模板必须区分 `raw_input_source`，并说明 raw input 是初期输入源而不是自动正式路线来源。
- 只有 `user_confirmed` 能进入正式版本路线。
- 如果 AIT 在已有对话中途接入，agent 应做 bootstrap checkpoint，把对话压缩成结构化 tracking 信息。
- bootstrap checkpoint 同时检查已有 `raw_input/`，但只索引和选择性读取。
- bootstrap checkpoint 记录已确认事实、用户目标、暴露问题、未决问题和候选检查项；候选项必须保持未确认状态。
- `auto it self improve` 如果暴露出 self improve workflow itself 的不足，必须作为 second-order improvement 一并处理或写入后续计划。

### 14. Projection Consistency（投影一致性）

- SQLite 是 run、decision、handoff 等事实的唯一来源；Markdown projection 只是可读投影。
- `context index` 只把与 SQLite 中 `decision_id` 和 status 一致的 decision projection 作为当前上下文。
- orphan/stale projection 必须被跳过并报告，避免测试、demo 或旧环境留下的 Markdown 文件伪装成当前结论。
- `handoff validate` 应把 orphan/stale projection 作为无效状态提示，推动 agent 在交接前清理或迁移记录。
- demo/test 历史可以保存在 `examples/` 或文档中，但必须说明测试目的和数据边界，不能默认成为当前项目 decision。

### 15. 模糊检索增强

- 当用户只记得“之前好像说过某个现象”时，提供本地候选检索入口。
- 检索层组合 BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）。
- 检索结果只能作为候选入口，不能替代 SQLite、plans、handoff、`run_id`、`decision_id` 和 topic evidence 的明确证据链。

## 后续 Backlog

这些条目是 `global plan backlog`（全局计划待办）。当用户以后提出上下文管理、历史检索、topic 管理或证据关联相关的新能力时，agent 必须先检查这里和 `plans/version_iterations.md` 的未覆盖能力，再决定是否延续已有路线；如果匹配，不要另开独立 plan 分支。

### semantic retrieval

- v0.19 已覆盖轻量模糊检索：BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）。
- 后续只在轻量方案主观收益不足且用户接受复杂度时，再评估更重的本地 embedding（把文本变成稠密数值向量的模型）或外部服务。
- 检索始终只能作为补充入口，不能替代 SQLite、plans、handoff 和 evidence run IDs 的明确证据链。

### topic evidence link

- topic 证据关联：把 topic 与相关 run、decision、artifact、handoff 建立可查询关联。
- 目标是让 agent 能回答“这个 topic 当时依据哪些实验、结论和工件”，而不需要人工逐个翻找。
- v0.16 已覆盖 run、decision、artifact 的最小可用关联；handoff 强关联可在后续按需要补充。

### topic lifecycle management

- topic 生命周期管理：支持 topic rename、merge、delete、prune，以及更明确的 reopen history。
- 目标是长期维护 topic archive，避免 archive 自身变成新的上下文噪音。
- 所有删除或 prune 行为必须保守，不能破坏已有证据链。

### topic plan and multi-thread topic binding

- topic plan：为每个 topic 提供局部计划和任务状态，包含 goal、non_goals、todo、doing、done、blocked、acceptance、stop_conditions、escalation_conditions、evidence。
- topic scoped handoff（topic 级交接）：为单个 topic 生成独立 handoff，避免多 Codex thread 并行时互相覆盖 `handoffs/latest_handoff.md`。
- topic_id 绑定：写入命令按 `--topic-id`、`AUTO_ITER_TOPIC_ID`、default topic 的顺序解析 topic；多个 open topic 场景下不能静默错绑。
- global plan 瘦身：global plan 保留长期方向、topic 模板、跨 topic 总览规则、升级规则和 backlog；topic 细节放入 topic plan、topic handoff 和 project board。

## 版本路线

### v0.1：本地状态闭环

状态：done。

范围：

- SQLite 状态库。
- run、metric、artifact、decision、handoff、route check。
- `run exec` 执行命令并捕获日志。
- run summary 和 error summary。
- version task tracking。

### v0.2：Codex 入口能力

状态：done。

目标：用户在 Codex CLI 内只表达任务，Codex agent 根据入口 skill 自动调用 `auto-iter`，不需要用户退出 Codex 或手写绝对路径。

任务：

- 提供可安装的短命令入口 `auto-iter`。
- 新增或调整 Codex 入口 skill，让 agent 在任务开始、实验前、实验后、任务结束时自动调用对应命令。
- 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- 提供一次端到端演示：从 Codex 会话内恢复状态、route check、run exec、decision add、handoff generate。

### v0.3：raw_input 使用边界和 handoff 校验

状态：done。

目标：让原始输入材料有固定落点和明确读取边界，同时减少交接字段缺失。

任务：

- `init` 创建 `raw_input/`。
- `AGENTS.md` 和入口 skill 明确 `raw_input/` 只能在初次开始项目或明确缺失信息时读取。
- 从 `raw_input/` 找到的新信息必须沉淀回 tracking 信息。
- 增加 handoff 完整性校验。

### v0.4：路线关系增强和动态载入上下文

状态：done。

目标：减少重复路线误判，并按标题索引和摘要读取历史，减少 token 占用。

任务：

- 记录路线关系字段，并落地参数空间被部分否定后的 route check 拦截。
- 保留 reopen condition 输出；方法替代的自动判断后续可继续增强。
- 建立 handoff、decision、run summary 的标题索引。
- 先读目录和摘要，需要时再读详细内容。

### v0.5：自然语言接力入口和细节读取入口

状态：done。

目标：用户不需要记具体命令，只用自然语言短句让 Codex agent 完成 session 结束、session 接力和历史细节查阅。

任务：

- 在 Codex entry skill 中写明自然语言触发短句和对应动作。
- session 结束短句触发 handoff 生成、handoff 校验，以及按任务需要提交推送。
- session 接力短句触发 doctor、resume、context index 和固定读取顺序。
- 细节查阅短句触发 context index，然后由 agent 选择合适的文件和标题运行 context show。
- README 和 entry skill 明确 `auto-iteration` 是固定工具名，不随算法项目名称变化。
- README 添加好例子，说明如何结束 session、如何开启新 session、如何查阅某个细节。

### v0.6：auto it self improve 系统改进沉淀能力

状态：done。

目标：用户明确调用 `auto it self improve` 后，agent 能从已经解决的具体问题中抽取通用改进，并把改进落到 auto_iteration 系统合适的位置。

任务：

- 新增 `auto-it-self-improve` skill，让 `auto it self improve` 成为明确触发短句，而不是自动后台行为。
- 定义抽象流程：具体问题复盘、通用问题抽取、改进落点选择、候选补丁生成、验证、提交。
- 定义禁止写入的内容：具体项目名、具体数据集、一次性参数、临时路径、只对单次对话成立的细节。
- 定义可写入的内容：通用流程规则、触发语句、文件选择规则、测试覆盖、文档示例、CLI 或模板缺口。
- 增加检查清单，要求每次执行都说明抽象依据和被排除的具体细节。
- 安装流程同步安装 `auto-it-self-improve` skill，并用测试覆盖。
- 安装后自检 `python3`、`auto-iter` 命令和必要 skills 是否 ready。

### v0.7：intent checkpoint 意图检查点

状态：done。

目标：用户用自然语言进入计划、执行、结果或结束阶段时，agent 先得到检查清单，再决定是否更新计划、检查路线、记录实验、记录结论或生成 handoff。

任务：

- 新增 `auto-iter intent check --text "<用户原话>"`。
- 支持计划、执行前、结果后、session 结束四类阶段提示。
- 明确该命令只输出检查清单，不直接写状态、不直接运行实验。
- 更新 entry skill、workflow skill、README、AGENTS 和初始化模板。
- 用测试覆盖命令输出和 v0.7 模板。

### v0.8：中途记录黑盒入口

状态：done。

目标：用户在长对话中可以只说“中途记录一下”，agent 使用和 session 结束相同的状态保存范围保存当前接力点，但不默认提交或推送。

任务：

- 新增 `auto-iter checkpoint save --text "<用户原话>"`。
- 让 `intent check` 识别中途记录类短句。
- 更新 entry skill、workflow skill、README、AGENTS 和初始化模板。
- 用测试覆盖命令输出、意图识别和 v0.8 模板。

### v0.9：低假设初始化和 bootstrap checkpoint

状态：done。

目标：新目标项目初始化时不污染业务计划；中途接入已有对话时，通过 bootstrap checkpoint 记录已确认上下文；self improve 能处理自身流程不足的二阶改进。

任务：

- 将 `auto-iter init` 生成的 plans 模板改成低假设模板。
- 在模板中增加来源标注规则和正式路线准入规则。
- 在 entry skill 和 README 中说明中途初始化后的 bootstrap checkpoint。
- 在 self improve skill 中增加 second-order improvement 处理规则。
- 用测试覆盖低假设初始化模板和 self improve skill 安装内容。

### v0.10：raw_input bootstrap 初期输入源

状态：done。

目标：新项目初始化时检查已有 `raw_input/`，把它作为初期输入源选择性沉淀，同时避免 `init` 自动读取或污染正式路线。

任务：

- 初始化模板加入 `raw_input_source` 来源标签。
- entry skill 在新项目初始化流程中使用 `context index --include-raw-input`。
- 有 raw input 时只读取相关章节，并用 `--allow-raw-input` 明示读取边界。
- README、AGENTS 和 tests 覆盖该流程。

### v0.11：安装管理卸载能力

状态：done。

目标：让用户能安全卸载并重新安装 AIT，用于验证安装和初始化流程，而不误删项目状态。

任务：

- 新增 `auto-iter uninstall`。
- 卸载已安装命令和 Codex skills。
- 保留项目 tracking 状态目录。
- README、AGENTS、entry skill 和 tests 覆盖卸载边界。

### v0.12：卸载时项目状态选择权

状态：done。

目标：卸载 AIT 时给用户选择是否删除项目过程产物，并说明每个项目状态目录的内容。

任务：

- `auto-iter uninstall` 打印项目状态目录说明。
- 交互终端询问是否删除项目状态目录。
- 非交互默认保留项目状态。
- 支持 `--keep-project-state` 和 `--remove-project-state`。
- 测试覆盖默认保留和显式删除。

### v0.13：Topic Archive 按需载入

状态：done。

目标：以 topic 为单位保存和恢复长期上下文，避免新 session 默认载入已经沉入历史的问题方向。

任务：

- 新增 `topics` 和 `topic_events` SQLite 账本。
- 新增 `active`、`archived_open`、`archived_satisfied` 三态，并保证最多一个 active topic。
- 新增 `auto-iter topic current/list/show/start/switch/satisfy`。
- 生成 `topics/active_topic.md`、`topics/index.md` 和 `topics/archive/<topic_id>.md` Markdown 投影。
- `context index` 和 handoff 接入 topic 摘要，但不默认展开 archived topic。
- README、AGENTS、entry skill 和 tests 覆盖 topic 切换确认规则。

### v0.14：跨平台安装和运行入口

状态：done。

目标：安装和运行入口同时覆盖 Windows Codex app、WSL/Linux Codex CLI、macOS Codex app，避免 Linux-only 或单用户绝对路径导致安装失败。

任务：

- 安装时按平台生成命令 wrapper：Windows 使用 `auto-iter.cmd`，WSL/Linux/macOS 使用 `auto-iter`。
- wrapper 使用当前 Python 解释器路径，不假设 `python3` 一定存在。
- README、AGENTS、entry/workflow skills 明确三个平台的安装命令。
- 清理稳定文档、skills、hook 中的单机绝对路径。
- 测试覆盖 wrapper 生成和稳定文档扫描。

### v0.15：投影一致性和 demo 历史边界

状态：done。

目标：避免 Markdown projection 与 SQLite 事实账本不一致时污染恢复上下文，同时允许 demo/test 历史保留为能力验证材料。

任务：

- `context index` 只索引仍能在 SQLite 中找到同 `decision_id` 和 status 的 decision projection。
- `context index` 对 orphan/stale decision projection 输出 warning，不把其标题当作当前上下文。
- `handoff validate` 将 orphan/stale decision projection 视为无效状态。
- README、AGENTS、entry/workflow skills 说明 SQLite 是事实来源，projection 需要一致性校验。
- demo/test 历史保留在 `examples/`，并明确测试目的和示例数据边界。
- 测试覆盖孤儿 projection 的跳过、warning 和 handoff 校验失败。

### v0.16：Topic Evidence Link

状态：done。

目标：让 topic 与相关 run、decision、artifact 形成可查询证据链，并在 topic projection 和 handoff 中暴露摘要。

任务：

- 新增 topic evidence link 的 SQLite 记录。
- 新增 `auto-iter topic link` 和 `auto-iter topic evidence`。
- 在 topic projection、context index 和 handoff 中暴露证据关联入口。
- 更新文档、entry skill 和测试。

### v0.17：多操作系统安装路径体验增强

状态：done。

目标：安装器优先选择当前 shell 已在 `PATH` 中且可写的系统常见命令目录，避免默认安装到裸命令不可见的位置，同时不默认修改用户环境。

任务：

- 新增安装目录推荐逻辑。
- macOS/Linux/WSL 优先使用 `/opt/homebrew/bin`、`/usr/local/bin` 或用户本地命令目录中已在 `PATH` 且可写的目录。
- Windows 回落到用户 AppData 下的 AIT 应用命令目录。
- 保留 path hint，不默认写 shell startup 文件。
- 更新文档和测试。

### v0.18：Stop hook 静默 handoff 生成

状态：done。

目标：修复 Codex Stop hook 因 `auto-iter handoff generate` 输出普通文本而报非法 hook JSON 的问题，并保持 Windows、WSL/Linux、macOS 三系统兼容。

任务：

- `auto-iter handoff generate` 默认生成 handoff 但不输出普通 stdout。
- `.codex/hooks.json` 使用默认 `auto-iter handoff generate`。
- 新增 `auto-iter handoff generate --print-path` 作为人工调试输出。
- 不使用 shell 重定向、平台空设备或平台特定包装命令。

### v0.19：本地模糊检索增强

状态：done。

目标：让用户只记得“之前好像说过某个现象”时，能通过本地检索找到候选历史，并回到明确证据链。

任务：

- 新增 `auto-iter search index` 建立本地检索索引。
- 新增 `auto-iter search query --text "<用户原话>" --limit 10 --explain` 查询候选历史。
- 组合 BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）。
- 默认排除 `raw_input/`，保持 tracking 信息优先。
- 搜索结果回指 path、heading、`run_id`、`decision_id` 或 topic evidence，不能替代 SQLite、plans、handoff 和 evidence run IDs 的明确证据链。
- `search query` 在索引输入未变化时复用已有索引；索引输入变化时才刷新默认 tracking-information index（tracking-information index：由 plans、handoff、topics、decisions 和 run summaries 派生出的本地检索索引）。
- 搜索索引是派生数据；索引 stale（索引可能不是最新）只表示最近写入内容可能暂时搜不到，不表示原始 run、decision、topic、handoff 或 plan 记录丢失。

### v0.20：handoff Current Baseline 投影

状态：done。

目标：在 handoff 中直接给出当前开发主线入口，避免新 session 需要从 active decision、latest run、topic evidence 和 artifact 中重新拼装“当前干到哪里”。

任务：

- `handoff generate` 增加 `Current Baseline` 段。
- `Current Baseline` 从现有 SQLite run、decision、artifact 和 topic evidence 生成，不新增数据库表。
- README、entry skill、handoff validate 和测试覆盖该投影。

### v0.21：可选项目规则文件读取顺序

状态：done。

目标：项目根目录的 `AGENTS.md` 是可选的 Codex 规则文件，不是 AIT 状态源；handoff 只在它已经存在时列入读取顺序。

任务：

- `handoff generate` 检查项目根目录 `AGENTS.md` 是否存在。
- 文件存在时，读取顺序把它列在 handoff 前。
- 文件不存在时，读取顺序从 `handoffs/latest_handoff.md` 开始，不制造缺失文件提示。
- README、AGENTS、entry skill、workflow skill 和测试覆盖该边界。

### v0.22：子目录项目根目录发现

状态：done。

目标：AIT 命令在已初始化项目的子目录中运行时，自动找到最近的父级状态库，避免把子目录误当成新的项目根。

任务：

- CLI 根目录解析从当前目录向上查找最近的 `state/agent_state.db`。
- 未找到父级状态库时保留原行为，`init` 仍初始化当前目录。
- `run exec` 从解析后的项目根目录记录和执行命令；需要实际进入子目录时，由 `--command` 显式 `cd`。
- README、AGENTS、entry skill、workflow skill 和测试覆盖该边界。

同版本补充：安装产物 update 入口。

- 新增 `auto-iter update`，用于刷新已安装 wrapper 和 Codex skills。
- 默认只更新安装产物，保留 `state/`、`plans/`、`topics/`、`raw_input/`、`decisions/`、`runs/`、`handoffs/`，不执行 `init`。
- `auto-iter update --check-project` 只在当前目录已有 AIT 状态时运行 `doctor`，没有状态时提示 skipped。

### v0.23：topic_id 解析和 default topic 兼容层

状态：done。

目标：保留旧 `active topic` 兼容入口，同时建立 `topic_id` 写入路径和 resolved topic 可见性，为多 Codex thread 并行工作打基础。

任务：

- 新增统一 topic 解析：`--topic-id` 参数优先，其次 `AUTO_ITER_TOPIC_ID` 环境变量，最后回退 default topic。
- `auto-iter doctor` 输出 resolved topic 和来源。
- 文档把 `active topic` 解释为 default topic 兼容入口，不再解释成唯一正在工作的 topic。

### v0.24：topic plan 基础结构

状态：done。

目标：为每个 topic 增加 topic plan 事实源和 Markdown projection。

任务：

- 新增 `topic_plans` 表。
- 新增 `topic plan set/show/current` 命令。
- 生成 `topics/<topic_id>/plan.md` 和 default topic plan 兼容投影。
- `context index` 纳入 topic plan。

### v0.25：topic 内任务状态

状态：done。

目标：让 topic plan 具备类似 Jira 的 todo、doing、done、blocked、dropped 任务状态。

任务：

- 新增 `topic_plan_items` 表。
- 新增 `topic task add/set/list` 命令。
- done/blocked 任务可关联 run、decision、artifact。

### v0.26：topic 级 handoff 和 checkpoint

状态：done。

目标：为单个 topic 生成独立 handoff 和 checkpoint，避免多 thread 互相覆盖项目级 handoff。

任务：

- 新增 `topics/<topic_id>/latest_handoff.md`。
- `handoff generate` 和 `checkpoint save` 支持 `--topic-id`。
- 项目级 handoff 显示 default topic、最近更新 topic、open topic 和 blocked topic 摘要。

### v0.27：project board 跨 topic 总览

状态：done。

目标：提供类似 Jira 的项目级 topic 看板，不让 global plan 承担细任务。

任务：

- 生成 `topics/board.md`。
- 新增 `topic board` 命令。
- 总览 open、doing、blocked、recent done、ready to satisfy 的 topic 和 task。

### v0.28：context index 和 search 完整接入

状态：done。

目标：topic plan、topic handoff、project board 全部进入按需读取和本地搜索。

任务：

- `context index` 纳入 `topics/<topic_id>/plan.md`、`topics/<topic_id>/latest_handoff.md`、`topics/board.md`。
- search graph 增加 topic 到 plan、handoff、task、evidence 的关系边。

### v0.29：写入安全和多 thread 防错

状态：done。

目标：多个 open topic 场景下，写入命令不能静默落到错误 topic。

任务：

- 多 open topic 时，关键写入命令要求显式 `--topic-id`、`AUTO_ITER_TOPIC_ID` 或 `--allow-default-topic`。
- 写入输出必须显示 resolved topic 和来源。

### v0.30：global plan 瘦身和模板化

状态：done。

目标：把 global plan 调整为长期方向、topic 模板、升级规则和跨 topic 摘要规则，不承载 topic 细节。

任务：

- 从 global plan 移出单 topic 任务细节。
- 保留 topic 模板、project board 读取规则、升级到 active_plan/version_iterations 的规则。

### v0.31：docs、skills、安装同步

状态：done。

目标：让 Codex agent 能用自然语言稳定操作 topic plan、topic board 和 topic-scoped handoff。

任务：

- 更新 README、AGENTS、entry skill、workflow skill。
- 安装后同步 Codex skills。
- 增加自然语言触发规则和测试。

### v0.32：迁移和兼容清理

状态：done。

目标：旧项目平滑升级到 topic_id/default topic/topic plan 结构。

任务：

- 旧 `active topic` 自动映射为 default topic。
- 没有 topic plan 的旧 topic 自动生成空 plan。
- handoff validate 先 warning，再按后续版本收紧。

### 后续可选：更重的语义检索

状态：deferred。

任务：

- 若索引规模明显变大，先评估增量索引；增量索引指只更新变动文件对应的搜索文档和结构关系边。
- 若轻量模糊检索主观收益不足，再评估是否引入更重的本地 embedding（把文本变成稠密数值向量的模型）或外部服务。
- 更重检索只能作为补充入口，不能替代 SQLite、plans、handoff 和 evidence run IDs 的明确证据链。
