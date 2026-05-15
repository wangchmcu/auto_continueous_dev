# Active Plan

## 当前目标

- 使用 Codex 长周期算法迭代的本地状态闭环，并保持 tracking 信息优先于原始输入材料。

## 当前实施阶段

- 当前版本：v0.4。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- v0.3 已完成：`raw_input/` 读取边界和 handoff 完整性校验。
- v0.4 已完成：参数空间路线拦截、上下文标题索引和按需读取。
- 下一阶段：等 tracking 信息规模变大后，再评估是否加入语义检索。

## 下一步

1. 正常任务继续使用 `auto-iter doctor`、`auto-iter resume`、`auto-iter context index`。
2. 若需要读取具体历史，使用 `auto-iter context show --path <file> --heading "<heading>"`。
3. 若 tracking 信息规模明显变大，再评估语义检索。
4. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。
