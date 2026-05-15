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
- 新 Codex session 先读 `AGENTS.md`、handoff、global plan、version tracking、active plan。
- 后续增加 handoff 完整性校验，检查关键字段缺失。

### 5. 原始输入目录

- 每个项目开发目录可以有 `raw_input/`，用于存放原始输入材料或老项目导入材料。
- `raw_input/` 只在两种情况下读取：初次开始项目；后续开发中明确需要到原始输入里检索缺失信息。
- 正常迭代时应优先读取 `plans/`、`handoffs/`、`decisions/`、run summaries 和 SQLite 状态库。
- 理论上，工作 tracking 信息应该已经吸收并更新了 `raw_input/` 中的重要信息；如果二者冲突，默认以 tracking 信息为准，除非用户明确要求回到原始输入核对。
- 从 `raw_input/` 找到的新信息，必须沉淀回 `plans/`、`decisions/`、handoff 或 run summary，避免下次再次回查原始材料。

### 6. Codex 入口能力

- 提供 Codex 入口 skill：告诉 agent 什么时候调用 `auto-iter doctor`、`auto-iter resume`、`auto-iter route check`、`auto-iter run exec`、`auto-iter decision add`、`auto-iter handoff generate`。
- 提供短命令入口 `auto-iter`，避免每次写 `python3 /home/ryan/auto_iteration/tools/auto_iter.py`。
- 用户在 Codex CLI 中表达任务，agent 在同一个会话里调用命令；用户不需要退出 Codex CLI。
- 入口 skill 只负责流程触发和命令调用顺序；状态写入仍由 `auto_iteration` 完成。

### 7. 动态载入上下文

- 建立按标题索引的上下文读取方式：先读目录和摘要，需要时再读详细内容。
- handoff、decision、run summary、error summary 都应可被按需读取。
- 避免一次性把所有历史塞进上下文。

### 8. 自然语言接力入口

- 用户可以用自然语言短句触发固定流程，例如结束 session、恢复 session、查阅某个历史细节。
- Codex entry skill 负责把这些短句映射到 `auto-iter` 命令序列。
- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 等具体命令。

### 9. Auto It Self Improve（系统改进沉淀能力）

- `auto it self improve` 是固定触发短句和能力名，指 auto_iteration 的系统改进沉淀能力：用户和 agent 解决了一个具体使用问题后，agent 把这个问题抽象成通用能力改进，并更新到 auto_iteration 系统中。
- 这个能力不能自动触发，只能在用户明确点名 `auto it self improve` 或 `auto-it-self-improve` skill 名时触发。
- 输入是已解决的对话片段、相关文件改动、失败现象和最终处理方式；输出是对 auto_iteration 系统的通用改进建议或补丁。
- 改进落点由 agent 根据问题类型选择，例如 `AGENTS.md`、README、entry skill、workflow skill、CLI 命令、初始化模板、测试、plans 或 handoff 模板。
- 必须先抽象成通用规则，再写入系统；不得把具体项目名称、具体数据集、一次性参数、临时文件路径或用户当次私有场景直接写成系统规则。
- 每次执行都应说明“具体问题是什么”“抽象后的通用问题是什么”“为什么应该改这些文件”“哪些具体细节没有写入系统”。

### 10. Intent Checkpoint（意图检查点）

- Intent checkpoint（意图检查点）指：用户话语像是在进入计划、执行前、结果后或 session 结束阶段时，agent 先运行检查命令获取下一步清单。
- 该能力的目标是减少漏记计划、漏做 route check、漏写 decision、漏生成 handoff，而不是自动替代 agent 判断。
- `auto-iter intent check --text "<用户原话>"` 只输出检查清单；它不直接写 SQLite、不启动实验、不生成结论。
- Codex entry skill 负责在用户说“做个计划”“更新计划”“执行吧”“实施吧”“确定执行”“拿到结果了”“跑完数据了”“测试结束了”“结束当前 session”等相似短句时调用该命令。
- 检查结果必须继续落回现有明确流程：计划文件、`route check`、`run exec`、`decision add`、`handoff generate` 和 `handoff validate`。

### 11. 中途记录黑盒入口

- 中途记录黑盒入口指：用户在对话中只说“中途记录一下”“先保存当前状态”“做个阶段记录”等自然语言短句，agent 自动保存当前接力点。
- 这个入口和 session 结束使用相同的状态保存范围：检查当前计划、实验事实、结论和 handoff 是否需要更新，并生成可恢复的 handoff。
- 它和 session 结束的区别是：中途记录不表示当前 session 结束，不默认提交，不默认推送。
- `auto-iter checkpoint save --text "<用户原话>"` 是 agent 内部使用的命令；用户不需要记住它。
- 如果用户同时明确要求“提交”或“推送”，agent 才在 checkpoint 后执行对应 git 操作。

### 12. 后续可选语义检索

- 当 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
- 语义检索只能作为补充入口，不能替代 SQLite、plans 和 handoff 的明确证据链。

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

### 后续可选：语义检索

状态：deferred。

任务：

- 当 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
- 语义检索只能作为补充入口，不能替代 SQLite、plans 和 handoff 的明确证据链。
