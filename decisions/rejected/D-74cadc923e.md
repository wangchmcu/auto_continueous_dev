# 放弃 max_value_reward 错误目标函数

- decision_id: D-74cadc923e
- status: rejected
- evidence_run_ids: R-e037afb46d
- route_keywords: max_value_reward, 错误目标
- reopen_condition: 只有用户明确把任务目标改成奖励预测值变大时才允许重开。

## 结论
第 6 轮把目标改成奖励预测值变大，mean_absolute_error 上升到 7.8，偏离了最小化误差的设计。
