# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 当前版本：v0.1。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- 下一阶段进入 v0.2 前，先确认 global plan 的下一项优先级。

## 下一步

1. 生成 handoff 并确认新 session 能读取 `plans/version_iterations.md`。
2. 为 v0.2 选择下一项 global plan 能力，例如 handoff 完整性校验或按标题索引动态载入上下文。
3. 每次版本范围变化时，先更新 `plans/version_iterations.md`。
4. 会话结束前运行 `handoff generate`。
