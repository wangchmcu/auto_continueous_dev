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

- current_version: v0.5
- status: done
- goal: 完成自然语言短句触发 session 结束、session 接力和历史细节查阅。

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
- [x] 初始化模板同步到 v0.5。

## v0.5 距离 global plan

v0.5 覆盖了自然语言接力入口和细节读取入口。

v0.5 已覆盖的全局能力：

- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 的具体命令。
- session 结束、session 接力、细节查阅都有自然语言触发短句。
- Codex entry skill 明确这些短句对应的 agent 行为。
- README 提供假设场景下的好例子。

v0.5 之后仍未覆盖的全局能力：

- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## 后续版本方向

### v0.2

- done：Codex 入口能力已完成。

### v0.3

- done：raw_input 使用边界和 handoff 校验已完成。

### v0.4

- done：路线关系增强和动态载入上下文已完成。

### v0.5

- done：自然语言接力入口和细节读取入口已完成。

### 后续可选

- 在 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
