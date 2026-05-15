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

### 5. Codex 入口能力

- 提供 Codex 入口 skill：告诉 agent 什么时候调用 `auto-iter doctor`、`auto-iter resume`、`auto-iter route check`、`auto-iter run exec`、`auto-iter decision add`、`auto-iter handoff generate`。
- 提供短命令入口 `auto-iter`，避免每次写 `python3 /home/ryan/auto_iteration/tools/auto_iter.py`。
- 用户在 Codex CLI 中表达任务，agent 在同一个会话里调用命令；用户不需要退出 Codex CLI。
- 入口 skill 只负责流程触发和命令调用顺序；状态写入仍由 `auto_iteration` 完成。

### 6. 动态载入上下文

- 建立按标题索引的上下文读取方式：先读目录和摘要，需要时再读详细内容。
- handoff、decision、run summary、error summary 都应可被按需读取。
- 避免一次性把所有历史塞进上下文。

### 7. 后续可选语义检索

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

目标：用户在 Codex CLI 内只表达任务，Codex agent 根据入口 skill 自动调用 `auto-iter`，不需要用户退出 Codex 或手写绝对路径。

任务：

- 提供可安装的短命令入口 `auto-iter`。
- 新增或调整 Codex 入口 skill，让 agent 在任务开始、实验前、实验后、任务结束时自动调用对应命令。
- 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- 提供一次端到端演示：从 Codex 会话内恢复状态、route check、run exec、decision add、handoff generate。

### v0.3：handoff 校验和路线关系增强

目标：减少交接字段缺失和重复路线误判。

任务：

- 增加 handoff 完整性校验。
- 增加更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。

### v0.4：动态载入上下文

目标：按标题索引和摘要读取历史，减少 token 占用。

任务：

- 建立 handoff、decision、run summary 的标题索引。
- 先读目录和摘要，需要时再读详细内容。
- 增加任务状态命令，减少手工维护 Markdown 的出错概率。
