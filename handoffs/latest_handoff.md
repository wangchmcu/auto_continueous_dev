# Latest Handoff

## 当前目标
- 未设置；请在下一轮实验前明确当前优化目标。

## 当前快照
- root: /Users/ryan/Documents/auto_continueous_dev
- workdir: /Users/ryan/Documents/auto_continueous_dev
- branch: search_enhance
- commit: 08846e6ecd2215ca7243773bb0665d5a3ac80354
- latest_successful_run_id: R-9aef4d0a8d
- latest_failed_run_id: none
- global_plan: plans/global_plan.md
- version_task_tracking: plans/version_iterations.md
- active_plan: plans/active_plan.md
- active_topic: topics/active_topic.md
- topic_index: topics/index.md
- topic_board: topics/board.md

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

## Project Topic Links
- none

## Current Baseline
- accepted_start: decision D-ce44870328: Route check ignores reference metadata keywords
- accepted_result: run R-9aef4d0a8d: dataset=AIT:route_check_metadata_keyword_fix:v0.44 status=success
- why_current: v0.44 route check now matches rejected route keywords against the structured current-route projection only. Freeform summary and reference metadata such as baseline, provenance, artifacts, results, metrics, logs, source paths, run ids, and decision ids no longer trigger route blocks; exact config duplicates, current route identity, factor/search-space keywords, and parameter-space numeric checks remain active. Verified by full unittest suite.
- evaluation_entry: decisions/active/D-ce44870328.md
- provenance_entry: runs/R-9aef4d0a8d/config_resolved.json
- diagnostic_entry: not recorded
- last_confirmed_at: 2026-06-24T11:50:12.649890+00:00

## Topic Evidence Links
- none

## 最近成功实验
- R-9aef4d0a8d: dataset=AIT:route_check_metadata_keyword_fix:v0.44 status=success

## 当前有效结论
- D-ce44870328: Route check ignores reference metadata keywords evidence=R-9aef4d0a8d
  - v0.44 route check now matches rejected route keywords against the structured current-route projection only. Freeform summary and reference metadata such as baseline, provenance, artifacts, results, metrics, logs, source paths, run ids, and decision ids no longer trigger route blocks; exact config duplicates, current route identity, factor/search-space keywords, and parameter-space numeric checks remain active. Verified by full unittest suite.

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
1. AGENTS.md
2. handoffs/latest_handoff.md
3. plans/global_plan.md
4. plans/version_iterations.md
5. plans/active_plan.md
6. topics/active_topic.md
7. topics/board.md
8. state/agent_state.db
9. decisions（只信任 `auto-iter context index` 未标记为 orphan/stale 的 projection）。
10. 用 `auto-iter context index` 查看可按需读取的标题索引和 projection warnings。
11. 只有用户要求或确认切回 archived topic 时才读取 topics/archive/。
12. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。
13. 只有初次开始项目或明确缺失信息时才读取 raw_input/。
