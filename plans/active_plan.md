# Active Plan

## 当前目标

- 使用 Codex 长周期算法迭代的本地状态闭环，并保持 tracking 信息优先于原始输入材料。

## 当前实施阶段

- 当前版本：v0.7。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- v0.3 已完成：`raw_input/` 读取边界和 handoff 完整性校验。
- v0.4 已完成：参数空间路线拦截、上下文标题索引和按需读取。
- v0.5 已完成：用自然语言短句触发 session 结束、session 接力和细节查阅流程。
- v0.6 已完成：`auto it self improve` 系统改进沉淀能力。
- v0.7 已完成：intent checkpoint（意图检查点），用于在计划、执行、结果和结束阶段提示 agent 先做安全检查。
- 下一阶段：等 tracking 信息规模变大后，再评估是否加入语义检索。

## 下一步

1. 当用户话语像是在进入计划、执行、结果或结束阶段时，agent 先运行 `auto-iter intent check --text "<用户原话>"`。
2. `intent check` 只给检查清单，不直接写数据库、不直接启动实验、不替代 `route check`、`run exec`、`decision add` 或 handoff 命令。
3. 用户明确说 `auto it self improve` 时，agent 才运行系统改进沉淀流程。
4. 若 tracking 信息规模明显变大，再评估语义检索。
5. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。
