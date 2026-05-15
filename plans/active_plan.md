# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 当前版本：v0.2。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- 下一阶段：v0.3 handoff 校验和路线关系增强。

## 下一步

1. 设计 handoff 完整性校验的最小字段集合。
2. 设计路线关系增强的最小数据结构。
3. 每次版本范围变化时，先更新 `plans/version_iterations.md`。
4. 会话结束前运行 `handoff generate`。
