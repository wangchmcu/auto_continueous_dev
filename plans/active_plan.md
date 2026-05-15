# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 当前版本：v0.2。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- 下一阶段：v0.3 raw_input 使用边界和 handoff 校验。

## 下一步

1. 让 `init` 创建 `raw_input/`。
2. 明确 `raw_input/` 只在初次开始项目或明确缺失信息时读取。
3. 设计 handoff 完整性校验的最小字段集合。
4. 会话结束前运行 `handoff generate`。
