# Active Plan

## 当前目标

- 使用 Codex 长周期算法迭代的本地状态闭环，并保持 tracking 信息优先于原始输入材料。

## 当前实施阶段

- 当前版本：v0.5。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- v0.3 已完成：`raw_input/` 读取边界和 handoff 完整性校验。
- v0.4 已完成：参数空间路线拦截、上下文标题索引和按需读取。
- v0.5 已完成：用自然语言短句触发 session 结束、session 接力和细节查阅流程。
- v0.6 已计划：self-improvement 系统改进沉淀能力。
- 下一阶段：实现 self-improvement 的明确触发入口、抽象流程、文件落点选择和防污染检查。

## 下一步

1. v0.6 开始前，读取 `plans/global_plan.md` 中的 `v0.6：self-improvement 系统改进沉淀能力`。
2. 设计明确触发词，保证 self-improvement 不会自动后台触发。
3. 设计抽象流程，保证具体问题只作为证据，不原样写进系统规则。
4. 设计文件落点选择规则，让 agent 能判断改 README、skill、CLI、模板、测试或 plans。
5. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。
