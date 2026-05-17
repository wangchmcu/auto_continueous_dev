# Latest Handoff

## 当前目标
- 未设置；请在下一轮实验前明确当前优化目标。

## 当前快照
- root: /Users/ryan/Documents/auto_continueous_dev
- branch: dev
- commit: bd17759d9a642f002bd5e9322195fbb2804947b8
- latest_successful_run_id: none
- latest_failed_run_id: none
- global_plan: /Users/ryan/Documents/auto_continueous_dev/plans/global_plan.md
- version_task_tracking: /Users/ryan/Documents/auto_continueous_dev/plans/version_iterations.md
- active_plan: /Users/ryan/Documents/auto_continueous_dev/plans/active_plan.md
- active_topic: /Users/ryan/Documents/auto_continueous_dev/topics/active_topic.md
- topic_index: /Users/ryan/Documents/auto_continueous_dev/topics/index.md

## 当前 Topic
- none

## 最近成功实验
- none

## 当前有效结论
- none

## 已废弃且不要重复的路线
- none

## 未决假设
- none

## 下一步最小实验集合
1. 先运行 `auto-iter route check --config <file> --summary <中文路线说明>`。
2. 若允许，再用 `auto-iter run exec` 执行实验，或用 `auto-iter run start` 和 `auto-iter run finish` 分步写回指标和工件。
3. 实验后用 `auto-iter decision add` 写入结论状态。
4. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。

## 读取顺序
1. /Users/ryan/Documents/auto_continueous_dev/AGENTS.md
2. /Users/ryan/Documents/auto_continueous_dev/handoffs/latest_handoff.md
3. /Users/ryan/Documents/auto_continueous_dev/plans/global_plan.md
4. /Users/ryan/Documents/auto_continueous_dev/plans/version_iterations.md
5. /Users/ryan/Documents/auto_continueous_dev/plans/active_plan.md
6. /Users/ryan/Documents/auto_continueous_dev/topics/active_topic.md
7. /Users/ryan/Documents/auto_continueous_dev/state/agent_state.db
8. /Users/ryan/Documents/auto_continueous_dev/decisions
9. 用 `auto-iter context index` 查看可按需读取的标题索引。
10. 只有用户要求或确认切回 archived topic 时才读取 topics/archive/。
11. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。
12. 只有初次开始项目或明确缺失信息时才读取 raw_input/。
