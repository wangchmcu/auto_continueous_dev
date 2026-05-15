# Latest Handoff

## 当前目标
- 未设置；请在下一轮实验前明确当前优化目标。

## 当前快照
- root: /home/ryan/auto_iteration
- branch: master
- commit: 3e452f036ff89d8de8df6961f301da7d6cb633d3
- latest_successful_run_id: R-9723365f8f
- latest_failed_run_id: none
- version_task_tracking: /home/ryan/auto_iteration/plans/version_iterations.md
- active_plan: /home/ryan/auto_iteration/plans/active_plan.md

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
1. 先运行 `auto-iteration route check --config <file> --summary <中文路线说明>`。
2. 若允许，再运行实验并用 `auto-iteration run finish` 写回指标和工件。
3. 实验后用 `auto-iteration decision add` 写入结论状态。

## 读取顺序
1. /home/ryan/auto_iteration/AGENTS.md
2. /home/ryan/auto_iteration/handoffs/latest_handoff.md
3. /home/ryan/auto_iteration/plans/version_iterations.md
4. /home/ryan/auto_iteration/plans/active_plan.md
5. /home/ryan/auto_iteration/state/agent_state.db
6. /home/ryan/auto_iteration/decisions
7. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。
