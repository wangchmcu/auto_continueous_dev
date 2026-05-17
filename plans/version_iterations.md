# Version Iteration Tracking

## 说明

这个文件记录每次版本迭代的目标、任务状态、验收证据、后续方向，以及当前版本整体距离 `global plan` 的差距。`global plan` 的定义和完整清单在 `plans/global_plan.md`。它不是实验日志；实验事实仍然写入 `state/agent_state.db`，实验结论仍然写入 `decisions/`。

- `pending` 表示还没开始。
- `in_progress` 表示正在做。
- `done` 表示已经完成并有证据。
- `blocked` 表示被外部条件卡住。
- `deferred` 表示明确放到后续版本。

## 全局方案方向

- 详见 `plans/global_plan.md`。

## 当前版本

- current_version: v0.13
- status: done
- goal: 完成 Topic Archive MVP，让长期上下文可按 topic 归档和按需载入。

## v0.1 任务清单

- [x] 初始化目录：`state/`、`runs/`、`handoffs/`、`decisions/`、`plans/`。
- [x] 初始化 SQLite 数据库：记录 runs、metrics、artifacts、decisions、handoffs、route_checks。
- [x] 记录实验开始：`run start` 写入配置、数据集、命令、Git commit 和 Git branch。
- [x] 记录实验结束：`run finish` 写入状态、指标和工件路径。
- [x] 查询实验：`run list` 和 `run show`。
- [x] 记录结论：`decision add` 写入 active、rejected、superseded、open 状态。
- [x] 替代旧结论：`decision supersede` 把旧结论移动到 superseded。
- [x] 阻断重复路线：`route check` 检查重复配置以及 rejected/superseded 关键词。
- [x] 生成交接：`handoff generate` 生成 `handoffs/latest_handoff.md`。
- [x] 恢复交接：`resume` 输出下一轮应该先读的 handoff。
- [x] Codex Stop hook：`.codex/hooks.json` 调用 handoff 生成命令。
- [x] Codex skill：`skills/auto-iteration/SKILL.md` 记录使用流程。
- [x] 十轮 demo：验证从多轮实验到结论沉淀的闭环。
- [x] 版本任务跟踪：每个版本都有任务状态、验收证据和下一步方向。证据：本文件。
- [x] handoff 接入版本任务跟踪：新 session 能看到当前版本和下一步工程任务。证据：`auto_iteration/cli.py` 的 handoff 输出和测试。
- [x] 结束汇报规则：每次任务结束前报告当前版本号、本次完成项、当前版本内部剩余项、当前版本整体距离 `global plan` 的差距。证据：`AGENTS.md`。
- [x] 日志摘要：自动生成 `runs/<run_id>/summary.md` 和 `runs/<run_id>/logs/error_summary.md`。证据：`run finish` 和 `run exec` 测试。
- [x] 实验命令封装：自动执行命令并捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。证据：`run exec` 测试。

## v0.1 距离 global plan

v0.1 的定位是打底版本：先让实验事实、结论、计划和 handoff 有固定落点。它不是完整的 `global plan`。

v0.1 已覆盖的全局能力：

- 账本层基础：SQLite 已记录 run、metric、artifact、decision、handoff、route check。
- 叙事层基础：`decisions/`、`handoffs/`、`plans/` 已有固定入口。
- 流程层基础：`AGENTS.md`、skill、Stop hook 已有固定规则。
- 重复路线拦截基础：能按配置哈希和 rejected/superseded 关键词阻断明显重复路线。
- 日志分级基础：每个 run 已有 `summary.md` 和 `logs/error_summary.md`，原始 stdout/stderr/debug 日志保留在 `logs/` 下。
- 实验执行基础：`run exec` 能执行单条实验命令并自动写入状态库和日志文件。

v0.1 之后仍未覆盖的全局能力：

- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 可选的语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.1 验收标准

1. `python3 -m auto_iteration.cli doctor` 通过。
2. `python3 -Wd -m unittest discover -s tests -v` 通过。
3. `handoffs/latest_handoff.md` 包含版本任务跟踪文件路径。
4. `plans/version_iterations.md` 明确列出当前版本状态、已完成任务、未完成任务和后续版本方向。

## v0.2 任务清单

- [x] 提供可安装的短命令入口 `auto-iter`。证据：`install` 命令和安装测试。
- [x] 新增 Codex 入口 skill：`skills/auto-iteration-entry/SKILL.md`。
- [x] 入口 skill 指导 agent 在任务开始、实验前、实验后、任务结束时自动调用 `auto-iter`。
- [x] 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- [x] 提供端到端演示：测试覆盖 doctor、resume、route check、run exec、decision add、handoff generate。

## v0.2 距离 global plan

v0.2 覆盖了 Codex 入口能力：用户可以在 Codex CLI 内表达任务，agent 通过入口 skill 在同一会话内调用 `auto-iter`。

v0.2 已覆盖的全局能力：

- Codex 入口 skill：`auto-iteration-entry`。
- 短命令入口：`auto-iter`。
- 入口流程：doctor、resume、route check、run exec、decision add、handoff generate。
- 端到端演示：临时项目中通过已安装 `auto-iter` 完成完整流程。

v0.2 之后仍未覆盖的全局能力：

- raw_input 原始输入目录的读取边界和沉淀规则。
- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.3 任务清单

- [x] `init` 创建 `raw_input/`。
- [x] `AGENTS.md` 和入口 skill 明确 `raw_input/` 只能在初次开始项目或明确缺失信息时读取。
- [x] 从 `raw_input/` 找到的新信息必须沉淀回 tracking 信息。
- [x] 增加 `handoff validate`，检查 handoff 关键章节和路径。

## v0.3 距离 global plan

v0.3 覆盖了 raw_input 使用边界和 handoff 完整性校验。

v0.3 已覆盖的全局能力：

- `raw_input/` 固定目录和默认不读取规则。
- `raw_input/` 显式读取许可：初次开始项目或缺失信息检索。
- handoff 校验：关键章节、global plan、version tracking、active plan 路径。

v0.3 之后仍未覆盖的全局能力：

- 更强的路线关系管理。
- 按标题索引动态载入上下文。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.4 任务清单

- [x] 增加 `--route-relation parameter-space` 和 `--route-param name:min:max`。
- [x] `route check` 能阻断被 rejected decision 覆盖的数值参数区间。
- [x] 增加 `context index`，默认索引 plans、handoff、decisions、run summaries、error summaries。
- [x] `context index` 默认排除 `raw_input/`。
- [x] 增加 `context show --path <file> --heading "<heading>"`，按标题载入单个章节。
- [x] 读取 `raw_input/` 需要显式 `--include-raw-input` 或 `--allow-raw-input`。

## v0.4 距离 global plan

v0.4 覆盖了路线关系增强和动态上下文载入。

v0.4 已覆盖的全局能力：

- 参数空间级 rejected route 阻断。
- 标题索引读取。
- 按需载入单个 Markdown 章节。
- raw_input 默认排除。

v0.4 之后仍未覆盖的全局能力：

- 自然语言接力入口：用户只说结束 session、继续项目、查阅细节，agent 自动调用固定命令序列。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.5 任务清单

- [x] 在 `auto-iteration-entry` skill 中增加自然语言触发短句。
- [x] “结束当前 session”触发 handoff 生成、handoff 校验，并按任务需要提交推送。
- [x] “继续这个 auto-iteration 项目”触发 doctor、resume、context index 和固定读取顺序。
- [x] “查阅某个结论或实验细节”触发上下文索引，然后按需读取具体章节。
- [x] README 增加好例子：如何结束 session、如何开启新 session、如何查阅细节。
- [x] README 和 entry skill 明确 `auto-iteration` 是固定工具名，不随算法项目名称变化。
- [x] 初始化模板同步到 v0.5。

## v0.5 距离 global plan

v0.5 覆盖了自然语言接力入口和细节读取入口。

v0.5 已覆盖的全局能力：

- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 的具体命令。
- session 结束、session 接力、细节查阅都有自然语言触发短句。
- Codex entry skill 明确这些短句对应的 agent 行为。
- README 提供假设场景下的好例子。

v0.5 之后仍未覆盖的全局能力：

- `auto it self improve` 系统改进沉淀能力：用户明确调用后，从具体对话问题中抽取通用改进并更新系统。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.6 任务清单

- status: done
- goal: 完成 `auto it self improve` 系统改进沉淀能力的入口、抽象流程、落点选择和防污染检查。
- [x] 新增 `auto-it-self-improve` skill，让 `auto it self improve` 成为明确触发短句，而不是自动后台行为。
- [x] 定义抽象流程：具体问题复盘、通用问题抽取、改进落点选择、候选补丁生成、验证、提交。
- [x] 定义文件落点选择规则：根据问题类型选择 `AGENTS.md`、README、entry skill、workflow skill、CLI 命令、初始化模板、测试、plans 或 handoff 模板。
- [x] 定义禁止写入内容：具体项目名、具体数据集、一次性参数、临时路径、只对单次对话成立的细节。
- [x] 定义可写入内容：通用流程规则、触发语句、文件选择规则、测试覆盖、文档示例、CLI 或模板缺口。
- [x] 增加检查清单：每次执行都要说明抽象依据、改动文件、验证方式、被排除的具体细节。
- [x] 安装流程同步安装 `auto-it-self-improve` skill，并用测试覆盖。
- [x] 安装后自检 `python3`、`auto-iter` 命令和必要 skills 是否 ready。

## v0.6 距离 global plan

v0.6 覆盖了 `auto it self improve` 系统改进沉淀能力。

v0.6 已覆盖的全局能力：

- 用户通过明确关键字触发系统改进沉淀。
- agent 能把具体对话问题抽象成通用能力改进。
- agent 能判断改进应该落在哪些系统文件中。
- 系统有防污染检查，避免把具体项目细节写进通用规则。
- 安装流程能检查必要依赖、命令和 skills 是否 ready。

v0.6 之后仍未覆盖的全局能力：

- intent checkpoint（意图检查点）：用户说“更新计划”“执行吧”“拿到结果了”等阶段切换短句时，agent 先检查是否需要更新计划、route check、run exec、decision add 或 handoff。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.7 任务清单

- status: done
- goal: 完成自然语言阶段切换的 intent checkpoint（意图检查点）。
- [x] 新增 `auto-iter intent check --text "<用户原话>"`，识别计划、执行前、结果后、session 结束四类阶段。
- [x] `intent check` 输出 agent 下一步检查清单，但不直接写数据库、不直接运行实验。
- [x] 入口 skill 和 workflow skill 明确：用户说“做个计划”“更新计划”“执行吧”“实施吧”“确定执行”“拿到结果了”“跑完数据了”“测试结束了”等相似短句时，agent 先运行 `intent check`。
- [x] README 增加使用场景和好例子，说明用户不用记命令，agent 在 Codex CLI 内调用。
- [x] 初始化模板、当前计划和版本跟踪同步到 v0.7。
- [x] 用测试覆盖 `intent check` 输出和模板版本更新。

## v0.7 距离 global plan

v0.7 覆盖了自然语言阶段切换的安全检查入口。

v0.7 已覆盖的全局能力：

- 计划阶段：提醒 agent 检查 `plans/active_plan.md`、`plans/version_iterations.md` 和必要的 `plans/global_plan.md`。
- 执行前阶段：提醒 agent 在实验路线前运行 `auto-iter route check`，并只在命令、配置、数据、指标和工件明确时使用 `auto-iter run exec`。
- 结果后阶段：提醒 agent 收集 metrics 和 artifact，再用有证据的 `run_id` 写 decision。
- session 结束阶段：提醒 agent 生成并校验 handoff，按用户要求提交和推送。

v0.7 之后仍未覆盖的全局能力：

- 中途记录黑盒入口：用户只说“中途记录一下”时，agent 使用和 session 结束相同的状态保存范围，但不默认提交推送。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.8 任务清单

- status: done
- goal: 完成中途记录黑盒入口。
- [x] 新增 `auto-iter checkpoint save --text "<用户原话>"`，用于生成并校验当前接力点。
- [x] 明确中途记录和 session 结束使用相同的状态保存范围；区别是中途记录不默认结束会话、不默认提交、不默认推送。
- [x] `intent check` 能识别“中途记录一下”“先保存当前状态”“做个阶段记录”等短句，并提示 agent 调用 checkpoint save。
- [x] 更新 entry skill、workflow skill、README、AGENTS 和初始化模板，让用户侧入口保持黑盒。
- [x] 用测试覆盖 checkpoint save、意图识别和 v0.8 模板。

## v0.8 距离 global plan

v0.8 覆盖了中途主动记录的黑盒入口。

v0.8 已覆盖的全局能力：

- 用户不需要知道 `active_plan`、`version_iterations`、decision、handoff 等内部落点。
- 用户可以只说“中途记录一下”，agent 在同一个 Codex session 内保存当前接力点。
- 中途记录默认不提交、不推送，只有用户明确要求提交或推送时才执行 git 操作。

v0.8 之后仍未覆盖的全局能力：

- 低假设初始化：新目标项目初始化时不应自动生成业务路线。
- bootstrap checkpoint：AIT 在对话中途接入时，应结构化记录已确认上下文。
- self improve 二阶改进：self improve 暴露自身能力缺口时，应同时迭代 self improve 流程。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.9 任务清单

- status: done
- goal: 完成低假设初始化、bootstrap checkpoint 和 self improve 二阶改进规则。
- [x] 将 `auto-iter init` 生成的 `plans/` 模板改为低假设模板。
- [x] 初始化模板明确 `当前业务目标：待用户定义`。
- [x] 初始化模板加入来源标注：`user_confirmed`、`repo_observed`、`conversation_summary`、`agent_inferred`、`proposed_not_accepted`。
- [x] 初始化模板明确 `agent_inferred` 和 `proposed_not_accepted` 不能进入正式版本路线。
- [x] entry skill 增加新项目初始化和中途接入 bootstrap checkpoint 流程。
- [x] README 增加低假设 init 和 bootstrap checkpoint 说明。
- [x] self improve skill 增加 second-order improvement 规则。
- [x] 用测试覆盖低假设初始化模板和 self improve skill 安装内容。

## v0.9 距离 global plan

v0.9 覆盖了低假设初始化和 self improve 二阶改进能力。

v0.9 已覆盖的全局能力：

- 新目标项目初始化不再默认写入 AIT 自身版本路线。
- 中途接入已有对话时，agent 有明确 bootstrap checkpoint 流程。
- 候选检查项必须带来源标签，正式路线需要用户确认。
- self improve 能识别并处理 self improve workflow itself 的不足。

v0.9 之后仍未覆盖的全局能力：

- 初始化 bootstrap 的 raw_input 初期输入源检查仍需明确：有 raw input 时应索引并选择性沉淀，不应让 `init` 自动吞入目录。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.10 任务清单

- status: done
- goal: 让新项目初始化时把已有 `raw_input/` 作为初期输入源检查，同时保持低假设和非自动吞入边界。
- [x] 初始化模板加入 `raw_input_source` 来源标签。
- [x] 初始化模板要求 agent 运行 `context index --include-raw-input` 检查已有原始材料。
- [x] entry skill 要求只按需读取 raw input 相关章节，并用 `--allow-raw-input` 明示越过默认边界。
- [x] README 和 AGENTS 明确：`raw_input/` 为空则继续；有内容则索引、选择性读取、沉淀回 tracking。
- [x] 保持 `auto-iter init` 不自动读取 raw input，避免核心命令吞入大体量或未确认材料。
- [x] 用测试覆盖初始化模板和安装后的 entry skill 内容。

## v0.10 距离 global plan

v0.10 覆盖了 raw input 作为初始 bootstrap 输入源的流程化入口。

v0.10 已覆盖的全局能力：

- 初次初始化时 raw input 不再只是“可选缺失信息来源”，而是被纳入 bootstrap 索引检查。
- raw input 读取仍保持显式、选择性、可追踪。
- `raw_input_source` 能和 `user_confirmed`、`repo_observed`、`conversation_summary` 等来源区分。

v0.10 之后仍未覆盖的全局能力：

- 安装管理缺少安全卸载入口：用户要验证初始化流程时，需要能卸载已安装命令和 skills，但不能误删项目状态。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.11 任务清单

- status: done
- goal: 增加 `auto-iter uninstall`，支持卸载后重新安装 AIT。
- [x] 新增 `uninstall` CLI 子命令。
- [x] 卸载默认移除 `~/.local/bin/auto-iter` 和安装到 Codex 的 AIT skills。
- [x] 卸载不删除项目状态目录：`state/`、`plans/`、`raw_input/`、`decisions/`、`runs/`、`handoffs/`。
- [x] 卸载拒绝删除不是当前 AIT checkout 安装的 `auto-iter` wrapper。
- [x] README、AGENTS 和 entry/workflow skills 说明卸载边界。
- [x] 用测试覆盖卸载行为和安装后的 entry skill 文案。

## v0.11 距离 global plan

v0.11 覆盖了 AIT 安装产物的安全卸载和重装验证入口。

v0.11 已覆盖的全局能力：

- 用户可以让 agent 卸载并重新安装 AIT，不必手动清理命令或 skills。
- 卸载和项目状态清理分离，降低误删长期 tracking 信息的风险。

v0.11 之后仍未覆盖的全局能力：

- 卸载时还需要给用户选择权：是否一并删除项目状态目录，并解释这些目录保存什么。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.12 任务清单

- status: done
- goal: 卸载 AIT 时默认保留项目状态，但让用户选择是否一并删除，并说明目录内容。
- [x] `auto-iter uninstall` 输出 `state/`、`plans/`、`raw_input/`、`decisions/`、`runs/`、`handoffs/` 的简要说明。
- [x] 交互终端中，无显式参数时询问是否删除项目状态目录。
- [x] 非交互执行默认保留项目状态，避免 CI 或 agent 调用卡住。
- [x] 新增 `--keep-project-state` 和 `--remove-project-state` 显式选择。
- [x] 用测试覆盖默认保留和显式删除两条路径。
- [x] 更新 README、AGENTS 和 entry/workflow skills。

## v0.12 距离 global plan

v0.12 覆盖了卸载流程中的项目状态选择权。

v0.12 已覆盖的全局能力：

- 用户卸载 AIT 时能看到项目状态目录说明。
- 用户可以选择只卸载安装产物，或连同过程产物一起删除。
- 自动化场景不会因为交互询问而挂住。

v0.12 之后仍未覆盖的全局能力：

- Topic Archive：按 topic 归档、默认只载入当前 active topic，并支持确认后切回历史 topic。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.13 任务清单

- status: done
- goal: 实现 Topic Archive MVP，让任何时刻只有一个 active topic，其它 topic 进入 archive 并按需恢复。
- [x] 新增 `topics` 和 `topic_events` SQLite 表，记录 topic 状态和生命周期事件。
- [x] 新增 `active`、`archived_open`、`archived_satisfied` 三种状态，并保证最多一个 active topic。
- [x] 新增 `auto-iter topic current/list/show/start/switch/satisfy`。
- [x] 切换或开启新 topic 时，把旧 active topic 保存为 `archived_open`。
- [x] `topic satisfy` 把当前 active topic 保存为 `archived_satisfied`，且不表示永久结束。
- [x] 生成 `topics/active_topic.md`、`topics/index.md` 和 `topics/archive/<topic_id>.md`。
- [x] `context index` 纳入 topic 投影，handoff 只放 active topic 短摘要和 topic index 路径。
- [x] 更新 AGENTS、README、entry skill 和 workflow skill：语义疑似切 topic 时必须先问用户“是不是已经切入新的 topic 了？”。
- [x] 用测试覆盖 topic 生命周期、投影、handoff、context index 和安装后的 entry skill 文案。

## v0.13 距离 global plan

v0.13 覆盖了 Topic Archive 的最小可用闭环。

v0.13 已覆盖的全局能力：

- topic 级状态账本：SQLite 记录 topic 当前状态和 lifecycle events。
- 单 active topic 约束：默认上下文只载入当前 active topic。
- archive 双语义：`archived_open` 表示未完成但已归档；`archived_satisfied` 表示阶段性满足但可重开。
- Markdown 投影：人类和 Codex 可通过 `topics/active_topic.md`、`topics/index.md` 和 archive 文件按需读取。
- handoff 和 context index 只暴露 topic 摘要入口，不默认展开历史 topic。

v0.13 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配；当前只在 Codex entry skill 中要求用户确认后切 topic。
- topic 与 run/decision/artifact 的强关联查询；当前 MVP 保存摘要和恢复入口，未实现专门 evidence link 表。
- 更细粒度的 topic merge、rename、delete 或 prune 能力。
- 后续可选：语义检索。当 topic、decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.13 验收标准

1. `auto-iter topic start` 能创建 active topic，并生成 `topics/active_topic.md` 和 `topics/index.md`。
2. 开启或切换 topic 时，旧 active topic 自动变成 `archived_open`，且 SQLite 中最多只有一个 active topic。
3. `auto-iter topic satisfy` 能把 active topic 变成 `archived_satisfied`，并保留可重开提示。
4. `auto-iter context index` 能索引 topic 投影，handoff 能输出 active topic 和 topic index 路径。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## 后续版本方向

### v0.2

- done：Codex 入口能力已完成。

### v0.3

- done：raw_input 使用边界和 handoff 校验已完成。

### v0.4

- done：路线关系增强和动态载入上下文已完成。

### v0.5

- done：自然语言接力入口和细节读取入口已完成。

### v0.6

- done：`auto it self improve` 系统改进沉淀能力。

### v0.7

- done：intent checkpoint（意图检查点），用于自然语言阶段切换前的安全检查。

### v0.8

- done：中途记录黑盒入口。

### v0.9

- done：低假设初始化、bootstrap checkpoint 和 self improve 二阶改进规则。

### v0.10

- done：初始化 bootstrap 的 raw_input 初期输入源索引和选择性沉淀规则。

### v0.11

- done：AIT 安装管理的安全卸载和重装验证入口。

### v0.12

- done：卸载时项目状态目录的可选删除和目录内容说明。

### v0.13

- done：Topic Archive MVP，支持单 active topic、archive 双状态、topic CLI、Markdown 投影和按需上下文入口。

### 后续可选

- 在 topic、decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
