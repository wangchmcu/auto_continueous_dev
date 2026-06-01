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

- current_version: v0.42
- status: done
- previous_goal: v0.41 完成 rejected experiment recording（被拒绝实验记录），让外部或历史失败实验能用 `run import` 进入 run summary，再用 rejected decision 阻断重复路线。
- goal: 完成 worktree execution context（worktree 执行现场）：共享 AIT 项目根负责 `.auto_iter/` 状态写入，每个窗口或 run 的 workdir 负责实验命令实际执行和 Git 状态采集。

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
- [x] 卸载默认移除安装目录中的 `auto-iter` wrapper 和安装到 Codex 的 AIT skills。
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

## v0.14 任务清单

- status: done
- goal: 让安装和运行入口覆盖 Windows Codex app、WSL/Linux Codex CLI、macOS Codex app 三类环境。
- [x] 安装时按平台生成 wrapper：Windows 为 `auto-iter.cmd`，WSL/Linux/macOS 为 `auto-iter`。
- [x] wrapper 使用当前 Python 解释器路径，不再假设 `python3` 一定存在。
- [x] 卸载时能识别并移除当前 checkout 安装的 POSIX 和 Windows wrapper。
- [x] README、AGENTS、entry skill、workflow skill 明确三个平台安装命令。
- [x] 清理稳定文档、skills、hook 中的 Linux-only 和单用户绝对路径。
- [x] 测试覆盖 wrapper 生成逻辑和稳定安装文档扫描。

## v0.14 距离 global plan

v0.14 覆盖了 Codex 入口能力的跨平台安装和运行要求。

v0.14 已覆盖的全局能力：

- Windows Codex app：安装入口支持 `py -m auto_iteration.cli install` 或 `python -m auto_iteration.cli install`，命令 wrapper 为 `auto-iter.cmd`。
- WSL/Linux Codex CLI：安装入口支持 `python3 -m auto_iteration.cli install`，命令 wrapper 为 `auto-iter`。
- macOS Codex app：安装入口支持 `python3 -m auto_iteration.cli install` 或 `python -m auto_iteration.cli install`，命令 wrapper 为 `auto-iter`。
- 稳定规则和文档不再写死某个 Linux 用户源码路径或当前 macOS checkout 路径。

v0.14 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配。
- topic 与 run/decision/artifact 的强关联查询。
- topic rename、merge、delete、prune 等生命周期管理增强。

## v0.14 验收标准

1. wrapper 生成测试覆盖 POSIX 和 Windows 两种命令文件。
2. 稳定文档扫描不再发现单用户源码路径。
3. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.15 任务清单

- status: done
- goal: 让 context index 和 handoff validate 以 SQLite 为事实来源校验 decision projection，并把 demo/test 历史保存在带目的说明的 example 文档中。
- [x] `context index` 跳过 SQLite 中不存在的 orphan decision projection，并输出 warning。
- [x] `context index` 跳过 SQLite status 不一致的 stale decision projection，并输出 warning。
- [x] `handoff validate` 把 orphan/stale decision projection 视为 invalid。
- [x] 清理根目录 `decisions/` 中十轮 demo 的孤儿 projection。
- [x] `examples/ten_round_demo` 明确测试目的和示例数据边界。
- [x] README、AGENTS、entry skill、workflow skill 说明 projection 只在 SQLite 一致时才是当前上下文。
- [x] self improve skill 增加 demo/test 历史与 projection 分类步骤。
- [x] 测试覆盖孤儿 projection 的跳过、warning 和 handoff 校验失败。

## v0.15 距离 global plan

v0.15 覆盖了 projection consistency（投影一致性）能力：Markdown 投影不再能脱离 SQLite 事实账本独立污染上下文。

v0.15 已覆盖的全局能力：

- SQLite 是 decision 的事实来源，`decisions/` 只是可读投影。
- `context index` 默认只列出 SQLite 中仍存在且 status 一致的 decision projection。
- orphan/stale projection 会被报告，且 `handoff validate` 会失败提醒清理。
- demo/test 历史可以保留，但必须放在 `examples/` 或文档中说明测试目的和数据边界。

v0.15 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配。
- topic 与 run/decision/artifact 的强关联查询。
- topic rename、merge、delete、prune 等生命周期管理增强。

## v0.15 验收标准

1. 孤儿 decision projection 不进入 `context index` 的当前上下文标题。
2. `context index` 对孤儿或状态不一致的 decision projection 输出 warning。
3. `handoff validate` 对孤儿或状态不一致的 decision projection 返回 invalid。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.16 任务清单

- status: done
- goal: 实现 topic evidence link（topic 证据关联）MVP，让 topic 与 run、decision、artifact 形成可查询证据链。
- [x] 新增 `topic_evidence_links` SQLite 表，记录 `topic_id`、`evidence_type`、`evidence_id`、摘要和创建时间。
- [x] 新增 `auto-iter topic link`，可把 run、decision、artifact 关联到指定 topic。
- [x] 新增 `auto-iter topic evidence`，按 topic 查询已关联证据。
- [x] `topics/active_topic.md` 和 archive topic projection 增加 `Evidence Links` 章节。
- [x] handoff 增加当前 topic 的 `Topic Evidence Links` 摘要。
- [x] README、AGENTS、entry skill 和 workflow skill 说明证据关联入口。
- [x] 测试覆盖 topic evidence link、projection、handoff 和安装后的 skill 文案。
- [x] `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.16 距离 global plan

v0.16 覆盖 topic evidence link（topic 证据关联）的最小可用闭环。

v0.16 已覆盖的全局能力：

- topic 可以显式关联相关 run、decision 和 artifact。
- agent 可以通过 `auto-iter topic evidence --topic-id <id>` 查询某个 topic 的证据链。
- 当前 active topic projection 和 handoff 能暴露证据摘要，恢复上下文时不需要逐个翻找 SQLite 表。

v0.16 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配。
- topic rename、merge、delete、prune 等生命周期管理增强。

## v0.16 验收标准

1. `auto-iter topic link` 能把已有 run、decision、artifact 绑定到 topic，并拒绝不存在的证据 ID。
2. `auto-iter topic evidence` 能列出 topic 关联的 run、decision、artifact 和摘要。
3. topic projection、context index 和 handoff 都能暴露 topic evidence link 入口。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.17 任务清单

- status: done
- goal: 改善多操作系统安装路径选择，让 `auto-iter` 优先安装到当前 shell 已认可的标准命令目录，同时避免默认修改用户环境。
- [x] 新增安装目录选择逻辑：优先使用已在 `PATH` 且可写的系统常见命令目录。
- [x] macOS/Linux/WSL 无合适目录时回落到 `~/.local/bin`，并继续使用 path hint。
- [x] Windows 无合适目录时回落到用户 `LOCALAPPDATA` 下的 AIT 应用命令目录。
- [x] 保持安装器默认不修改 shell 启动文件、不注入 PATH。
- [x] README、AGENTS、entry skill 和 workflow skill 说明安装路径选择规则。
- [x] 测试覆盖 POSIX 标准目录优先、用户目录回落、Windows 用户目录回落。
- [x] `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.17 距离 global plan

v0.17 覆盖 Codex 入口能力中“跨平台安装和运行入口”的体验增强部分。

v0.17 已覆盖的全局能力：

- 安装器不再固定落到可能不在当前 shell `PATH` 中的用户目录。
- 在 macOS/Linux/WSL 上，优先使用当前 shell 已认可且可写的标准命令目录。
- 在 Windows 上，保守回落到用户 AppData 下的应用命令目录。
- 默认不修改用户 shell 配置，减少对用户环境的侵入。

v0.17 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配。
- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令；当前版本只提示，不自动写。

## v0.17 验收标准

1. 安装目录选择测试覆盖 POSIX 标准目录优先和用户目录回落。
2. 安装目录选择测试覆盖 Windows 用户目录回落。
3. `install` 不默认修改 shell 启动文件。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.18 任务清单

- status: done
- goal: 修复 Codex Stop hook 因 `auto-iter handoff generate` 输出普通文本而被解析为非法 JSON 的问题，并保持 Windows、WSL/Linux、macOS 三系统兼容。
- [x] `auto-iter handoff generate` 默认写入 handoff 和 SQLite 记录但不向 stdout 输出普通文本。
- [x] `.codex/hooks.json` 的 Stop hook 使用默认 `auto-iter handoff generate`。
- [x] 新增 `auto-iter handoff generate --print-path`，只在人工调试时输出 `generated <path>`。
- [x] 避免使用 shell 重定向、`/dev/null`、`NUL`、`cmd.exe` 或 POSIX shell 包装命令，保证 Windows、WSL/Linux、macOS 三系统都走同一个 CLI 参数。
- [x] 测试覆盖 Stop hook 命令、默认静默 handoff 生成行为和显式调试输出。
- [x] `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.18 距离 global plan

v0.18 覆盖 Codex 入口能力中 Stop hook 自动生成 handoff 的三系统兼容修复。

v0.18 已覆盖的全局能力：

- Stop hook 不再向 stdout 输出普通文本，避免 Codex 把普通文本当 hook JSON 解析时报错。
- handoff 自动生成仍由 `auto-iter` 负责，SQLite 记录和 `handoffs/latest_handoff.md` 仍保持更新。
- handoff 生成命令默认静默，不依赖某个操作系统的 shell 语法；人工调试需要输出路径时显式加 `--print-path`。

v0.18 之后仍未覆盖的全局能力：

- 自动语义检索和相似度匹配。
- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令。

## v0.18 验收标准

1. `auto-iter handoff generate` stdout 为空，且仍生成 `handoffs/latest_handoff.md`。
2. `.codex/hooks.json` 的 Stop hook 使用默认 `auto-iter handoff generate`。
3. Stop hook 命令不依赖 shell 重定向或平台特定空设备。
4. `auto-iter handoff generate --print-path` 显式输出生成路径，供人工调试使用。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.19 任务清单

- status: done
- goal: 加入本地模糊检索增强，保持现有 SQLite、标题、`run_id`、`decision_id` 和 topic evidence 证据链不变。
- [x] 新增 `auto-iter search index`，从 plans、handoff、topics、有效 decision projection、run summary、error summary 建立本地检索索引。
- [x] 新增 `auto-iter search query --text "<用户原话>" --limit 10 --explain`，用于“之前是不是说过某个现象”这类模糊历史查找。
- [x] 默认排除 `raw_input/`；只有显式 `search index --include-raw-input` 才纳入原始输入材料。
- [x] 检索组合 BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）。
- [x] search query 输出候选来源、路径、heading、相关 id、信号解释和下一步 `context show` 命令。
- [x] 测试覆盖 search index、search query、默认排除 raw input、decision 到 evidence run 的结构关系扩展。
- [x] README、AGENTS、entry skill 和 workflow skill 说明 fuzzy historical recall（模糊历史回忆）入口。
- [x] `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.19 距离 global plan

v0.19 覆盖 `global plan` 中的模糊检索增强能力，但只采用轻量本地方案。

v0.19 已覆盖的全局能力：

- 用户可以用自然语言模糊描述历史现象，agent 通过 `auto-iter search query` 得到候选上下文。
- 检索层不调用额外 LLM（大语言模型）服务，不引入复杂本地模型依赖。
- 检索结果会回指到 path、heading、`run_id`、`decision_id` 或 topic evidence，仍以明确证据链为准。

v0.19 之后仍未覆盖的全局能力：

- 更重的本地 embedding（把文本变成稠密数值向量的模型）或外部向量服务；仅在轻量方案收益不够且用户接受复杂度时评估。
- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令。

## v0.19 验收标准

1. `auto-iter search index` 能建立检索文档和结构关系边。
2. `auto-iter search query --text "<模糊问题>" --explain` 能返回候选 path、heading、相关 id 和下一步读取命令。
3. 默认搜索不返回 `raw_input/` 内容。
4. 命中 decision 时能通过 graph 结构关系带出 evidence run。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.20 任务清单

- status: done
- goal: 让 handoff 默认给出一个最小 `Current Baseline` 投影，恢复时先看到当前主线入口，而不是在 active decision、latest run、topic evidence 和 artifact 之间重新拼装。
- [x] `handoff generate` 增加 `Current Baseline` 段。
- [x] `Current Baseline` 从现有 active decision、latest successful run、run config、topic artifact evidence 生成，不新增数据库表。
- [x] `handoff validate` 把 `Current Baseline` 作为必需章节。
- [x] README、global plan、active plan 和 entry skill 说明新 session 先读 `Current Baseline`。
- [x] 测试覆盖 `Current Baseline` 对 accepted start、accepted result、evaluation entry、provenance entry、diagnostic entry 的投影。

## v0.20 距离 global plan

v0.20 没有扩张新的事实源；它把当前主线入口落实到 handoff projection，仍以 SQLite、decision、run、artifact 和 topic evidence 为证据链。

v0.20 已覆盖的全局能力：

- fresh session 能在 handoff 里直接看到当前开发起点和证据入口。
- `Current Baseline` 只放入口，不复制完整评估规则、产物来源或诊断详情。
- 缺失 `Current Baseline` 的 handoff 会被 `handoff validate` 判为无效。

v0.20 之后仍未覆盖的全局能力：

- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令。

## v0.20 验收标准

1. `auto-iter handoff generate` 默认静默，并生成 `Current Baseline`。
2. `Current Baseline` 能从已有 run、decision、artifact 和 topic evidence 生成入口。
3. `auto-iter handoff validate` 对缺失 `Current Baseline` 的 handoff 返回 invalid。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.21 任务清单

- status: done
- goal: 项目根目录 `AGENTS.md` 是可选 Codex 规则文件，不是 AIT 状态源；handoff 只在它已经存在时列入读取顺序。
- [x] `handoff generate` 根据项目根目录 `AGENTS.md` 是否存在动态生成读取顺序。
- [x] 缺失 `AGENTS.md` 时，读取顺序从 `handoffs/latest_handoff.md` 开始。
- [x] 已存在 `AGENTS.md` 时，读取顺序把它列在 handoff 前。
- [x] README、AGENTS、entry skill、workflow skill 和 global plan 说明该文件是可选项目规则入口。
- [x] 测试覆盖存在和不存在 `AGENTS.md` 两种读取顺序。

## v0.21 距离 global plan

v0.21 没有新增事实源，也不让 AIT 初始化凭空创建项目规则文件。它把 handoff 读取顺序和初始化行为对齐，减少新项目接管时的误导。

v0.21 已覆盖的全局能力：

- 新项目缺少项目级 `AGENTS.md` 时不会出现缺失必读项。
- 已有项目规则文件仍能在新 session 中优先被看到。
- `AGENTS.md` 的定位保持为稳定流程规则，不承载实验历史或 AIT 状态。

v0.21 之后仍未覆盖的全局能力：

- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令。

## v0.21 验收标准

1. 没有项目根目录 `AGENTS.md` 时，`auto-iter handoff generate` 的读取顺序不包含该路径。
2. 存在项目根目录 `AGENTS.md` 时，`auto-iter handoff generate` 的读取顺序把该路径列在 handoff 前。
3. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.22 任务清单

- status: done
- goal: AIT 命令在已初始化项目的子目录中运行时能找到最近父级状态库；同时提供 `auto-iter update` 刷新安装产物，默认保留项目状态、不运行 `init`。
- [x] CLI 根目录解析从当前目录向上查找最近的 `state/agent_state.db`。
- [x] 未找到父级状态库时保留原行为，`init` 仍初始化当前目录。
- [x] `doctor` 从子目录运行时报告父级项目根目录。
- [x] 当时的 `run exec` 从解析后的项目根目录记录和执行命令，不在子目录新建 `runs/`；执行目录规则已由 v0.42 取代。
- [x] README、AGENTS、entry skill、workflow skill 和 global plan 说明子目录运行边界。
- [x] 测试覆盖子目录运行 `doctor` 和 `run exec`。
- [x] 新增 `update` CLI 子命令，复用安装路径选择、卸载安全检查和安装自检。
- [x] `auto-iter update` 默认只更新安装产物，不删除或创建项目状态目录。
- [x] 新增 `--check-project`：当前目录已有 AIT 状态时运行 `doctor`；没有状态时输出 skipped，不执行 `init`。
- [x] README、AGENTS、entry skill 和 workflow skill 说明“更新 AIT”使用 `auto-iter update`。
- [x] 测试覆盖 update 保留项目状态、刷新安装产物、不默认初始化项目、可选 project check。
- [x] `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.22 距离 global plan

v0.22 没有新增事实源；它修复了命令入口在真实工作目录可能位于项目子目录时的根目录定位问题，并覆盖 Codex 入口能力中的安装产物更新入口，减少用户把“更新 AIT”和“初始化项目状态”混在一起的风险。

v0.22 已覆盖的全局能力：

- AIT 命令可从已初始化项目的子目录恢复到同一个 SQLite 状态库。
- 当时的 `run exec` 状态记录仍落在项目根目录，避免子目录生成孤立的 `runs/`；执行目录规则已由 v0.42 的 workdir 规则取代。
- agent 文档当时明确：实验需要子目录执行时，把 `cd path/to/workdir && ...` 写入 `--command`；v0.42 后该写法只保留为旧版兼容回退。
- 用户可用一个命令刷新 `auto-iter` wrapper 和 installed skills。
- update 默认保留项目状态，避免误删长期 tracking 信息。
- update 默认不运行 `init`，避免在错误目录创建 AIT 状态。
- 需要项目健康检查时通过 `--check-project` 显式触发。

v0.22 之后仍未覆盖的全局能力：

- topic rename、merge、delete、prune 等生命周期管理增强。
- 显式 opt-in 的 shell PATH 配置写入命令。

## v0.22 验收标准

1. 在已初始化项目子目录运行 `auto-iter doctor`，输出的 root 是父级项目根目录。
2. 在已初始化项目子目录运行 `auto-iter run exec`，run 记录和 `runs/` 目录写入父级项目根目录。
3. `auto-iter update` 默认刷新安装产物但不创建项目状态。
4. `auto-iter update --check-project` 能在已有项目状态时运行 doctor，没有状态时跳过。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.23 任务清单

- status: done
- goal: 建立 topic_id 解析和 default topic 兼容层，保留旧 active topic 恢复入口，同时为多 Codex thread 并行写入打基础。
- [x] 新增统一 topic 解析：`--topic-id` 参数优先，其次 `AUTO_ITER_TOPIC_ID` 环境变量，最后回退 default topic。
- [x] `auto-iter doctor` 输出 resolved topic 和来源。
- [x] README、AGENTS、entry skill、workflow skill 和 global plan 把 `active topic` 解释为 default topic 兼容入口。
- [x] 测试覆盖显式参数、环境变量、default topic 三种解析来源。

## v0.23 距离 global plan

v0.23 是 topic_id 驱动路线的兼容层，不删除旧 active topic，也不改变 run、decision、route check、search 的事实语义。

v0.23 已覆盖的全局能力：

- 多 Codex thread 可通过显式 topic_id 或环境变量表达工作 topic。
- 单 thread 和旧项目仍可使用 default topic 作为默认恢复入口。
- doctor 能暴露 resolved topic，降低错绑风险。

v0.23 之后仍未覆盖的全局能力：

- topic plan 基础结构。
- topic 内任务状态。
- topic 级 handoff 和 checkpoint。
- project board 跨 topic 总览。
- topic plan、topic handoff、project board 的 context index/search 接入。
- 多 open topic 场景下的写入安全收紧。
- global plan 瘦身和模板化。
- 旧 active topic 项目迁移和兼容清理。

## v0.23 验收标准

1. `auto-iter doctor` 在无 topic 时显示 resolved topic 为 none。
2. `AUTO_ITER_TOPIC_ID=<id> auto-iter doctor` 显示 resolved topic 来源为 environment。
3. 存在 default topic 且无显式参数或环境变量时，`auto-iter doctor` 显示 resolved topic 来源为 default_topic。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.24 任务清单

- status: done
- goal: 为每个 topic 增加 topic plan 事实源和 Markdown projection，覆盖局部目标、非目标、验收、停止条件和升级条件。
- [x] 新增 `topic_plans` 表。
- [x] 新增 `auto-iter topic plan set/show/current`。
- [x] 生成 `topics/<topic_id>/plan.md` 和 `topics/default_topic_plan.md`。
- [x] `context index` 纳入 topic plan。
- [x] README、AGENTS、entry skill、workflow skill 说明 topic plan 不能替代 decision 和 run evidence。
- [x] 测试覆盖 topic plan 设置、展示、default plan projection 和 context index。

## v0.24 距离 global plan

v0.24 完成 topic plan 的基础结构，但还没有 topic 级 handoff、project board 或多 open topic 写入安全收紧。

v0.24 已覆盖的全局能力：

- 每个 topic 可以拥有独立的局部计划。
- topic plan 已进入 SQLite 事实源和 Markdown projection。
- context index 能按需发现 topic plan。

v0.24 之后仍未覆盖的全局能力：

- topic 级 handoff 和 checkpoint。
- project board 跨 topic 总览。
- topic plan、topic handoff、project board 的 search graph 接入。
- 多 open topic 场景下的写入安全收紧。
- global plan 瘦身和模板化。
- 旧 active topic 项目迁移和兼容清理。

## v0.24 验收标准

1. `auto-iter topic plan set --topic-id <id>` 写入 topic plan。
2. `auto-iter topic plan show --topic-id <id>` 输出同一份 plan。
3. `auto-iter topic plan current` 输出 default topic 的 plan。
4. `auto-iter context index` 包含 `topics/<topic_id>/plan.md` 和 `topics/default_topic_plan.md`。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.25 任务清单

- status: done
- goal: 为 topic plan 增加 topic 内任务状态，覆盖 todo、doing、done、blocked、dropped。
- [x] 新增 `topic_plan_items` 表。
- [x] 新增 `auto-iter topic task add/set/list`。
- [x] topic plan projection 按状态显示 Todo、Doing、Done、Blocked、Dropped。
- [x] README、AGENTS、entry skill、workflow skill 说明 topic task 是计划状态，不替代 decision 和 topic evidence。
- [x] 测试覆盖任务新增、状态更新、列表和 plan projection。

## v0.25 距离 global plan

v0.25 让 topic plan 具备类似 Jira 的局部任务看板，但还没有项目级跨 topic board，也没有 topic 级 handoff。

v0.25 已覆盖的全局能力：

- 单个 topic 内可以记录 todo、doing、done、blocked、dropped。
- topic plan projection 能按状态展示任务。

v0.25 之后仍未覆盖的全局能力：

- topic 级 handoff 和 checkpoint。
- project board 跨 topic 总览。
- topic plan、topic handoff、project board 的 search graph 接入。
- 多 open topic 场景下的写入安全收紧。
- global plan 瘦身和模板化。
- 旧 active topic 项目迁移和兼容清理。

## v0.25 验收标准

1. `auto-iter topic task add --topic-id <id>` 新增 topic task。
2. `auto-iter topic task set --item-id <id> --status doing` 更新任务状态。
3. `auto-iter topic task list --topic-id <id>` 显示任务状态。
4. `topics/<topic_id>/plan.md` 按状态展示任务。
5. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.26 任务清单

- status: done
- goal: 为单个 topic 生成独立 handoff 和 checkpoint，避免多个 Codex thread 互相覆盖项目级 handoff。
- [x] 新增 `topics/<topic_id>/latest_handoff.md`。
- [x] `handoff generate --topic-id <id>` 和 `checkpoint save --topic-id <id>` 写 topic 级 handoff。
- [x] `handoff validate --topic-id <id>` 校验 topic 级 handoff。
- [x] 项目级 handoff 增加 Topic Summary，显示 default topic、recent topic、open topic 和 blocked task 摘要。

## v0.26 验收标准

1. `auto-iter handoff generate --topic-id <id>` 默认静默，并只写 `topics/<topic_id>/latest_handoff.md`。
2. `auto-iter checkpoint save --topic-id <id> --text "<text>"` 生成有效 topic handoff。
3. 项目级 handoff 包含 `## Topic Summary`。
4. `python3 -Wd -m unittest discover -s tests -v` 通过。

## v0.27 任务清单

- status: done
- goal: 提供跨 topic 的 project board（项目 topic 总览：open、doing、blocked、done 和 ready to satisfy 摘要）。
- [x] 新增 `topics/board.md`。
- [x] 新增 `auto-iter topic board`。
- [x] board 显示 open topics、doing tasks、blocked tasks、recent done tasks、ready to satisfy topics。

## v0.27 验收标准

1. `auto-iter topic board` 输出 project board。
2. `topics/board.md` 与命令输出一致。
3. blocked task 和 recent done task 能在 board 中按 topic 找到。

## v0.28 任务清单

- status: done
- goal: topic plan、topic handoff、project board 进入 context index 和 search。
- [x] `context index` 纳入 `topics/<topic_id>/latest_handoff.md`。
- [x] search source type 区分 `topic_plan`、`topic_handoff`、`topic_board`。
- [x] search graph 通过 topic_id 连接 topic projection、topic plan、topic handoff 和 board。

## v0.28 验收标准

1. `auto-iter context index` 能看到 topic plan、topic handoff 和 topic board。
2. `auto-iter search index` 为 topic plan、topic handoff 和 topic board 建索引。
3. 搜索结果能回到明确 path、heading 和 topic_id。

## v0.29 任务清单

- status: done
- goal: 多 open topic 场景下，topic 级写入不能静默落到错误 topic。
- [x] topic 级写入按 `--topic-id`、`AUTO_ITER_TOPIC_ID`、default topic 解析。
- [x] 多 open topic 且隐式 default 写入时拒绝，除非显式 `--allow-default-topic`。
- [x] topic 级写入输出 resolved topic 和来源。

## v0.29 验收标准

1. `AUTO_ITER_TOPIC_ID=<id> auto-iter topic plan set ...` 能写入指定 topic。
2. 多 open topic 时，未显式绑定 topic 的写入被拒绝并提示 `--topic-id`、`AUTO_ITER_TOPIC_ID` 或 `--allow-default-topic`。
3. 显式 `--allow-default-topic` 时可以写 default topic。

## v0.30 任务清单

- status: done
- goal: global plan 保持长期方向、topic 模板、project board 读取规则和升级规则；单 topic 细节进入 topic plan、topic handoff 和 board。
- [x] global plan 明确不承载单 topic 任务细节。
- [x] project board 成为跨 topic 总览入口。
- [x] active_plan/version_iterations 继续记录 AIT 自身版本实施状态。

## v0.31 任务清单

- status: done
- goal: README、AGENTS 和 Codex skills 同步 topic_id 长期方案。
- [x] README 增加 topic board、topic-scoped handoff、topic checkpoint、migrate 和多 open topic 写入规则。
- [x] AGENTS 增加多 thread topic 绑定和 global plan 瘦身规则。
- [x] `auto-iteration-entry` 和 `auto-iteration` skills 同步命令和规则。
- [x] 安装测试覆盖新 skill 文案。

## v0.32 任务清单

- status: done
- goal: 旧项目平滑升级到 topic_id/default topic/topic plan 结构。
- [x] 新增 `auto-iter migrate`。
- [x] migrate 为没有 topic plan 的旧 topic 创建空 plan，并刷新 topic projections 和 board。
- [x] `handoff validate` 对缺 topic plan 的旧 topic 先 warning，不直接失败。

## v0.32 验收标准

1. `auto-iter migrate` 能为 legacy topic 创建 `topics/<topic_id>/plan.md`。
2. `auto-iter migrate` 输出 default topic 和 board 路径。
3. 缺 plan 的旧 topic 会在 `handoff validate` 中产生 warning，但 validate 仍可通过。

## v0.23-v0.32 实践期问题判定规则

这轮 topic_id 长期方案的测试覆盖了核心命令路径，但测试不可能完整覆盖用户后续真实实践。后续实践中遇到问题时，先把问题对照本轮开发过程和验收边界，再判断是功能 bug 还是功能缺失。

- 功能 bug：已经在 v0.23-v0.32 计划、任务清单、验收标准或文档规则中承诺过的行为，实际使用不符合承诺。例如显式 `--topic-id` 写错 topic、topic 级 handoff 覆盖项目级 handoff、多 open topic 时没有防错、migrate 没有给旧 topic 补空 plan、context/search 找不到已生成的 topic handoff。确认是 bug 时，不重新开 global plan 分支，直接沿本轮既有计划修复，并在对应版本记录下追加 bugfix 证据。
- 功能缺失：实践中出现的新需求没有被 v0.23-v0.32 的计划、任务清单、验收标准或文档规则承诺。例如 topic merge、topic rename、跨 topic 依赖图、自动从对话推断 topic 切换等。确认是功能缺失时，先回到 global plan backlog 或新增后续版本，再实施。
- 判定依据优先级：先看 `plans/version_iterations.md` 的 v0.23-v0.32 任务和验收标准，再看 `plans/global_plan.md` 的 topic plan 和 multi-thread topic binding 规则，然后看 README、AGENTS 和 skills 的用户入口说明，最后看测试只作为已覆盖路径的证据。
- 修复记录要求：bugfix 要写明复现输入、期望行为、实际行为、对应承诺位置、修复文件和验证命令；不要因为测试当时没有覆盖就自动判为功能缺失。

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

### v0.14

- done：跨平台安装和运行入口，覆盖 Windows Codex app、WSL/Linux Codex CLI、macOS Codex app。

### v0.15

- done：projection consistency（投影一致性）和 demo/test 历史边界。

### v0.16

- done：topic evidence link（topic 证据关联）MVP。

### v0.17

- done：多操作系统安装路径体验增强。

### v0.18

- done：Stop hook 默认静默 handoff 生成修复，避免 stdout 被 Codex 当 hook JSON 解析，并保持三系统兼容。

### v0.19

- done：本地模糊检索增强，覆盖 BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）。

### v0.20

- done：handoff `Current Baseline` 投影，恢复时先看到当前主线入口和证据入口。

### v0.21

- done：项目根目录 `AGENTS.md` 只在已经存在时进入 handoff 读取顺序，缺失时不创建、不报缺失。

### v0.22

- done：AIT 命令在已初始化项目子目录中自动使用最近父级状态库所在目录作为项目根；当时 `run exec` 仍从项目根启动命令，这条执行目录规则已由 v0.42 取代；安装产物 update 入口也已合入。

### v0.23

- done：topic_id 解析和 default topic 兼容层；`--topic-id`、`AUTO_ITER_TOPIC_ID`、default topic 三层解析，doctor 显示 resolved topic。

### v0.24

- done：topic plan 基础结构，新增 topic plan 事实源、投影和 `topic plan set/show/current`。

### v0.25

- done：topic 内 Jira 式任务状态，新增 todo、doing、done、blocked、dropped 任务项。

### v0.26

- done：topic 级 handoff 和 checkpoint，避免多 thread 覆盖项目级 handoff。

### v0.27

- done：project board 跨 topic 总览，承担类似 Jira 的项目级看板。

### v0.28

- done：topic plan、topic handoff、project board 接入 context index 和 search。

### v0.29

- done：写入安全和多 thread 防错，多个 open topic 时不能静默错绑 default topic。

### v0.30

- done：global plan 瘦身和模板化，只保留长期方向、topic 模板、跨 topic 摘要规则和升级规则。

### v0.31

- done：README、AGENTS、Codex skills 和安装同步。

### v0.32

- done：旧 active topic 项目平滑迁移和兼容清理。

### v0.33

- done：`search query` 按需刷新索引；索引输入签名未变化时复用已有索引，避免每次查询全量重建。
- done：新增 `search_index_meta` 记录默认索引和 raw-input 索引的输入签名、文档数、结构关系边数和 FTS 后端状态。
- done：新增 `state/search_index.lock` 重建锁；并发 search 中只有一个进程执行重建，其他进程可继续使用旧索引并打印 stale warning（stale warning：提示索引可能不是最新，不代表原始记录丢失）。
- done：README、AGENTS、Codex skills 已同步说明 search query 只在索引输入变化时刷新。
- evidence：`python3 -Wd -m unittest discover -s tests -v` 通过 60 个测试；真实 Valeo AIT 项目第二次同查询从约 5.25 秒降到约 0.05 秒；并行两个 search query 不再出现 `database is locked`。

### v0.34

- done：新增 topic evidence carryover check（topic 证据承接检查）规则：在既有 topic 或相邻工作区继续改代码前，必须读取 topic evidence、topic handoff/search 候选，并核对 current branch or worktree 是否包含相关历史修复。
- done：AGENTS、README、entry skill、workflow skill 已写明 topic plan alone is not enough；topic plan 是计划状态，不替代 run、decision、artifact 和 topic evidence 构成的证据链。
- evidence：新增 `test_topic_pitfall_carryover_rule_is_documented`，覆盖 AGENTS、README、两个 Codex skill 和版本记录。

### v0.35

- done：补强 topic plan carryover（topic plan 承接执行补强）：当前 topic 的目标、非目标、验收或下一步任务一旦在对话中形成、被采纳或变化，agent 不能只写聊天、checkpoint 或 handoff；必须更新既有 topic plan，并按需要添加 topic task。
- done：`auto-iter intent check` 增加通用 topic-plan-carryover 检查，覆盖“计划、方案、下一步、实施方向、开发方向、验收、不做、acceptance、todo”等表达；“新 session / 下一 session / 新会话 / 下一会话” 只是额外的高风险提示。
- done：README 和 entry skill 已同步说明 handoff 是投影，不应成为当前 topic 计划变化的唯一落点。
- evidence：新增 intent-check 测试断言 topic-plan-carryover 输出，并保留 next-session 场景作为子场景覆盖。

### v0.36

- done：补强 `auto-it-self-improve` skill：自进化修补前必须回查 `plans/version_iterations.md`、`plans/global_plan.md`、README、相关 skills 和测试里的历史承诺。
- done：自进化必须先判定 scope：功能 bug 表示已有承诺未兑现，按原需求对齐修复；功能缺失表示原设计未覆盖，先进入 backlog、当前版本计划或新增版本再实施；不确定时记录已查承诺和不确定原因。
- done：自进化必须基于第一性原则抽象通用能力，先说明要保护的系统不变量，例如事实源、证据链、状态流转、恢复边界或污染边界，避免只修字面症状、关键词或一次性表达。
- evidence：安装测试断言 `auto-it-self-improve` skill 包含历史回查、bug/feature gap 判定和 first principles 要求。

### v0.37

- done：project plan split（项目计划拆分）：被接管项目使用 `plans/project_plan.md` 记录项目长期计划，使用 `plans/project_record_rules.md` 记录项目定制的 AIT 记录规则；被接管项目里的 `plans/global_plan.md` 改为兼容入口。
- done：`auto-iter migrate` 会归档旧 `plans/global_plan.md`，生成 project plan split migration note，并保留既有 topic plan、topic task、topic evidence、handoff 和 SQLite 状态。
- done：`ownership-routing`（需求归属判断）：`auto-iter intent check` 在 AIT、auto-iter、update、migrate、search、handoff、skill 等请求中提示先判断计划归属。Do not write AIT tool work into the managed project's project plan or topic plan.
- done：handoff 和 resume 读取顺序优先列出 `plans/project_plan.md`、`plans/project_record_rules.md`，再列兼容 `plans/global_plan.md`，旧项目未迁移时仍能用旧入口恢复。
- done：README、AGENTS、entry skill、workflow skill、AIT global plan 和 active plan 同步说明 project plan split、`project_record_rules` 与 ownership-routing。
- evidence：新增 `test_project_plan_split_and_ait_ownership_routing_are_documented`、迁移测试、intent check 测试和 handoff snapshot 测试；完整验证命令记录在本次实现会话。

### v0.38

- done：project state single-dir layout（项目状态单目录布局）：新项目默认把 AIT 状态写入 `.auto_iter/`，包括 `state/agent_state.db`、`plans/`、`topics/`、`handoffs/`、`decisions/`、`runs/` 和 `raw_input/`。
- done：旧布局兼容：`auto-iter doctor`、`resume`、`context index`、`search query`、`handoff`、`topic`、`run`、`decision` 和 `route` 仍能识别已有 root-level `state/agent_state.db`。
- done：`auto-iter migrate --layout single-dir` 显式把旧 root-level AIT 状态目录移动到 `.auto_iter/`；如果 `.auto_iter/` 已存在且非空，迁移会停止，避免覆盖。
- done：`auto-iter doctor` 输出 `state_dir` 和 `layout`，让 agent 能直接看到 SQLite 和 Markdown projection 的实际落点。
- done：README、AGENTS、entry skill、workflow skill、AIT global plan 和 active plan 同步说明 `.auto_iter/`、旧布局兼容和单目录迁移命令。
- global plan distance：本版本覆盖了状态落点收敛、子目录项目根发现的双布局兼容、旧项目显式迁移和恢复入口可见性；仍未覆盖 topic 生命周期管理、增量索引和更重的本地 embedding（把文本变成稠密数值向量的模型）检索。
- evidence：新增默认单目录初始化、旧布局初始化、旧到新迁移、防覆盖迁移测试；完整验证命令记录在本次实现会话。

### v0.39

- done：README 和 AGENTS 明确区分“从未被 AIT 接管过的仓库先 `init`”与“旧版 AIT 项目升级才 `migrate`”，避免把结构迁移命令误用成首次接管入口。
- done：`auto-iter migrate` 在结构迁移完成后输出最小 follow-up checklist，覆盖 `doctor`、`project_record_rules`、`.auto_iter/rules/current_effective.md` 和空规则项目的 `rule add` 回填提示；既有 `rule add/list/show` 入口继续保留。
- done：AIT global plan、active plan 和 version tracking 同步记录这次迁移指导补强，保持工具本体记录闭环。
- evidence：新增 `test_migrate_prints_follow_up_checklist_and_rule_backfill_hint`；验证命令为 `python3 -m unittest tests.test_cli.CliTests.test_migrate_prints_follow_up_checklist_and_rule_backfill_hint -v`。
- acceptance：用户能从 README/AGENTS 看懂何时 `init`、何时 `migrate`；`migrate` 输出能直接指导迁移后的下一步。

### v0.40

- done：project-topic explicit tracking（项目计划和 topic 显式跟踪）：新增 `project_topic_links` SQLite 表，记录 `project_plan.md` 标题、topic_id、关系类型和中文说明。
- done：新增 `auto-iter project link-topic`、`auto-iter project topic-links` 和 `auto-iter topic project-links`，支持从项目计划标题和 topic 两侧查询同一条关联。
- done：topic plan、topic board 和 `plans/project_topic_links.md` 投影显示 project-topic link；`context index` 和 search 能按需发现该投影。
- done：README、AGENTS、entry skill、workflow skill、AIT global plan 和 active plan 明确这是双向跟踪，不是 project plan 与 topic plan 的自动内容同步。
- global plan distance：本版本覆盖了 project plan 与 topic plan 的显式关联；仍未覆盖 topic 生命周期管理、增量索引和更重的本地 embedding（把文本变成稠密数值向量的模型）检索。
- evidence：新增 `test_project_topic_links_are_queryable_from_both_sides_and_indexed`；完整验证命令记录在本次实现会话。

### v0.41

- done：新增 `auto-iter run import`，把外部工具、旧 Codex session 或手工 SIL 结果导入为普通 run，写入 `runs/<run_id>/summary.md` 并保留 metrics、artifacts、command 和 session。
- done：`auto-iter intent check` 识别 rejected experiment（被拒绝的实验：已经证明不能继续采用或不能合入的实验结果）表述，提示先 `run import`，再写 `decision add --status rejected`。
- done：`auto-iter checkpoint save` 对拒绝实验表述输出 `recording_debt_warning`，明确 checkpoint 不会自动创建 run 或 decision。
- done：README、AGENTS、entry skill、workflow skill、AIT global plan 和 active plan 同步说明 `auto-iter run import`、`route-keyword` 和 `reopen-condition` 的使用边界。
- global plan distance：本版本覆盖了外部/历史失败实验进入证据链的最小闭环；仍未覆盖 topic 生命周期管理、增量索引和更重的本地 embedding（把文本变成稠密数值向量的模型）检索。
- evidence：新增 `test_run_import_records_external_rejected_experiment_summary_for_decision_evidence`、`test_intent_check_flags_rejected_experiment_result_recording`、`test_checkpoint_save_warns_about_rejected_result_recording_debt` 和 `test_rejected_experiment_recording_is_documented`。

### v0.42

- done：新增 `AUTO_ITER_PROJECT_ROOT` 和全局 `--project-root`，用于指定共享 AIT 项目根，也就是 `.auto_iter/` 状态的读写位置。
- done：新增 `AUTO_ITER_WORKDIR`、全局 `--workdir` 和 run 级 `--workdir`，用于指定 workdir（实验命令实际运行目录，通常是某个 Git worktree）。
- done：run 记录新增 `project_root`、`workdir`、`git_dirty_count` 和 `git_status_short` 字段；Git 分支、Git 提交、未提交改动数量和状态摘要都从 workdir 采集。
- done：`run exec` 从 workdir 执行命令，run summary 显示共享 AIT 项目根、workdir、Git 分支、Git 提交和未提交改动数量。
- done：`doctor`、项目级 handoff 和 topic 级 handoff 显示 workdir，并把 branch/commit 绑定到该 workdir。
- done：README、AGENTS、entry skill、workflow skill、AIT global plan 和 active plan 同步说明多 Git worktree、多 Codex 窗口的使用方式。
- acceptance：`AUTO_ITER_PROJECT_ROOT` 和 `--project-root` 能让非项目根目录里的命令继续写入同一个 `.auto_iter/` 状态目录。
- acceptance：`AUTO_ITER_WORKDIR`、全局 `--workdir` 和 run 级 `--workdir` 能让命令在指定 workdir 执行，并把该 workdir 的 Git 状态写进 run summary。
- acceptance：旧版兼容方式 `cd path/to/workdir && ...` 只作为不支持 `--workdir` 的安装版本的回退说明。
- global plan distance：本版本覆盖了多 Git worktree、多 Codex 窗口场景下的执行现场固化；仍未覆盖 topic 生命周期管理、增量索引和更重的本地 embedding（把文本变成稠密数值向量的模型）检索。
- evidence：`python3 -Wd -m unittest discover -s tests -v` 通过 90 个测试；`python3 -m py_compile auto_iteration/cli.py` 通过；`python3 -m auto_iteration.cli doctor` 返回 state/database ok；`git diff --check` 通过。

### 后续可选

- 若轻量检索的主观收益不足，再评估是否引入更重的本地 embedding（把文本变成稠密数值向量的模型）或外部服务。
- 若索引文档规模继续增大，再评估增量索引；增量索引指只更新变动文件对应的搜索文档和结构关系边，而不是每次全量重建。
- 若用户再次提出 AIT update 功能开发，先读取 `plans/global_plan.md` 的 `self update workflow` backlog；该条记录了 2026-05-22 对 `ait update` 期望、风险和更稳语义的初版方向。
- 若迁移后发现某个被接管项目仍把 AIT 工具开发写入项目 topic plan，先按 ownership-routing 处理为 AIT 计划归属 bug，再补迁移或入口规则。
