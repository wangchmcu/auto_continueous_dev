# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 当前版本：v0.1。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- 下一阶段：v0.2 Codex 入口能力。

## 下一步

1. 提供可安装的短命令入口 `auto-iter`。
2. 新增或调整 Codex 入口 skill，让 agent 在 Codex CLI 会话内自动调用 `auto-iter`。
3. 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
4. 提供一次端到端演示：从 Codex 会话内恢复状态、route check、run exec、decision add、handoff generate。
