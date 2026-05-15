# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 当前版本：v0.1。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成核心闭环：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff。
- v0.1 剩余缺口：日志摘要和实验命令封装。

## 下一步

1. 补 `runs/<run_id>/summary.md` 和 `runs/<run_id>/logs/error_summary.md` 的自动生成。
2. 补实验命令封装，自动捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。
3. 每次版本范围变化时，先更新 `plans/version_iterations.md`。
4. 会话结束前运行 `handoff generate`。
