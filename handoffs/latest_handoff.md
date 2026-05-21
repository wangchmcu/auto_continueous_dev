# Latest Handoff

## 当前目标
- 未设置；请在下一轮实验前明确当前优化目标。

## 当前快照
- root: /home/ryan/auto_iteration
- branch: search_enhance
- commit: b43eb528c353bb3f5f6609edf04193047970fc21
- latest_successful_run_id: R-9723365f8f
- latest_failed_run_id: none
- global_plan: /home/ryan/auto_iteration/plans/global_plan.md
- version_task_tracking: /home/ryan/auto_iteration/plans/version_iterations.md
- active_plan: /home/ryan/auto_iteration/plans/active_plan.md
- active_topic: /home/ryan/auto_iteration/topics/active_topic.md
- topic_index: /home/ryan/auto_iteration/topics/index.md
- topic_board: /home/ryan/auto_iteration/topics/board.md

## 当前 Topic
- none

## Topic Summary
### Default Topic
- none

### Recently Updated Topics
- none

### Open Topics
- none

### Blocked Topic Tasks
- none

## Current Baseline
- accepted_start: decision D-7188530483: 十轮示例收敛到 weight 2.0 offset 1.5
- accepted_result: run R-9723365f8f: dataset=ten-round-demo status=success
- why_current: 第 10 轮使用 weight=2.0 和 offset=1.5，mean_absolute_error 达到 0.0。
- evaluation_entry: /home/ryan/auto_iteration/decisions/active/D-7188530483.md
- provenance_entry: /home/ryan/auto_iteration/runs/R-9723365f8f/config_resolved.json
- diagnostic_entry: /home/ryan/auto_iteration/runs/R-9723365f8f/artifacts/report.md
- last_confirmed_at: 2026-05-15T04:21:17+00:00

## Topic Evidence Links
- none

## 最近成功实验
- R-9723365f8f: dataset=ten-round-demo status=success
  - other: /home/ryan/auto_iteration/runs/R-9723365f8f/artifacts/report.md

## 当前有效结论
- D-7188530483: 十轮示例收敛到 weight 2.0 offset 1.5 evidence=R-9723365f8f
  - 第 10 轮使用 weight=2.0 和 offset=1.5，mean_absolute_error 达到 0.0。

## 已废弃且不要重复的路线
- D-74cadc923e: 放弃 max_value_reward 错误目标函数 evidence=R-e037afb46d
  - reopen_condition: 只有用户明确把任务目标改成奖励预测值变大时才允许重开。

## 未决假设
- none

## 下一步最小实验集合
1. 先运行 `auto-iter route check --config <file> --summary <中文路线说明>`。
2. 若允许，再用 `auto-iter run exec` 执行实验，或用 `auto-iter run start` 和 `auto-iter run finish` 分步写回指标和工件。
3. 实验后用 `auto-iter decision add` 写入结论状态。
4. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。

## 读取顺序
1. /home/ryan/auto_iteration/AGENTS.md
2. /home/ryan/auto_iteration/handoffs/latest_handoff.md
3. /home/ryan/auto_iteration/plans/global_plan.md
4. /home/ryan/auto_iteration/plans/version_iterations.md
5. /home/ryan/auto_iteration/plans/active_plan.md
6. /home/ryan/auto_iteration/topics/active_topic.md
7. /home/ryan/auto_iteration/topics/board.md
8. /home/ryan/auto_iteration/state/agent_state.db
9. /home/ryan/auto_iteration/decisions（只信任 `auto-iter context index` 未标记为 orphan/stale 的 projection）。
10. 用 `auto-iter context index` 查看可按需读取的标题索引和 projection warnings。
11. 只有用户要求或确认切回 archived topic 时才读取 topics/archive/。
12. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。
13. 只有初次开始项目或明确缺失信息时才读取 raw_input/。
