# Version Iteration Tracking

## 说明

这个文件记录每次版本迭代的目标、任务状态、验收证据和后续方向。它不是实验日志；实验事实仍然写入 `state/agent_state.db`，实验结论仍然写入 `decisions/`。

- `pending` 表示还没开始。
- `in_progress` 表示正在做。
- `done` 表示已经完成并有证据。
- `blocked` 表示被外部条件卡住。
- `deferred` 表示明确放到后续版本。

## 全局方案方向

- 账本层：SQLite 数据库记录实验、指标、工件、结论和 handoff，是事实来源。
- 叙事层：`decisions/`、`handoffs/`、`plans/` 记录人和 Codex 都能读懂的结论、交接和计划。
- 流程层：`AGENTS.md`、skills、hooks 记录稳定规则和自动化入口。

## 当前版本

- current_version: v0.1
- status: in_progress
- goal: 建立最小可用的本地状态闭环，让长周期算法迭代不会只依赖聊天上下文。

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
- [x] 结束汇报规则：每次任务结束前报告当前版本号、本次完成项、距离 global plan 的未完成项。证据：`AGENTS.md`。
- [ ] 日志摘要：自动生成 `runs/<run_id>/summary.md` 和 `runs/<run_id>/logs/error_summary.md`。
- [ ] 实验命令封装：自动执行命令并捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。

## v0.1 验收标准

1. `python3 -m auto_iteration.cli doctor` 通过。
2. `python3 -Wd -m unittest discover -s tests -v` 通过。
3. `handoffs/latest_handoff.md` 包含版本任务跟踪文件路径。
4. `plans/version_iterations.md` 明确列出当前版本状态、已完成任务、未完成任务和后续版本方向。

## 后续版本方向

### v0.2

- 自动执行实验命令。
- 自动捕获 stdout、stderr 和 debug 日志。
- 自动生成实验摘要和错误摘要。
- handoff 默认只引用摘要和证据路径，不粘贴原始日志。

### v0.3

- 增加按标题索引读取的上下文机制：先读目录和摘要，需要时再读详细记录。
- 增加 handoff 校验，检查关键字段是否缺失。
- 增加任务状态命令，减少手工维护 Markdown 的出错概率。
