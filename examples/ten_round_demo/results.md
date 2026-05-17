# Ten Round Demo Results

本次验收任务用于验证 AIT 能连续记录多轮 run、metrics、artifacts、decisions、route check 和 handoff。示例数据是人为构造的线性拟合任务，不代表本项目自身的算法目标，也不应作为当前项目结论进入根目录 `decisions/` 上下文。

示例任务：用 `预测值 = weight * x + offset` 拟合固定数据 `目标值 = 2.0 * x + 1.5`。核心指标是 `mean_absolute_error`（平均绝对误差，单位是目标值单位，越低越好）。

第 6 轮故意偏离设计：`max_value_reward`（错误目标函数，含义是奖励预测值变大，而不是最小化误差）让误差明显变差。该路线已写入 `rejected` 结论，并通过 `route check` 验证会被拦截。

```text
round    run_id         objective            mean_absolute_error
round01  R-481372b321   minimize_error                    8.250000
round02  R-1fa52164a7   minimize_error                    6.000000
round03  R-567cf300f6   minimize_error                    3.750000
round04  R-1097fed3c6   minimize_error                    1.350000
round05  R-c222ca947b   minimize_error                    1.500000
round06  R-e037afb46d   max_value_reward                  7.800000
round07  R-22676f1529   minimize_error                    1.000000
round08  R-c8ef75e4a3   minimize_error                    0.500000
round09  R-8935b891ae   minimize_error                    0.100000
round10  R-9723365f8f   minimize_error                    0.000000
```

## 演示中记录到状态库的结论

这些 ID 是当次 demo 运行的证据链样例，只说明 AIT 具备把实验结论写入状态库和 projection 的能力。它们不属于当前项目根状态库的有效结论；如果要保留这类历史，应保留在 `examples/` 文档中，并写明测试目的和示例数据边界。

- `D-74cadc923e`: `rejected`，放弃 `max_value_reward` 错误目标函数。证据 run 是 `R-e037afb46d`。
- `D-7188530483`: `active`，十轮示例收敛到 `weight=2.0` 和 `offset=1.5`。证据 run 是 `R-9723365f8f`。

## 重复路线拦截证据

第 6 轮后，再次检查同一错误目标路线，`route check` 返回：

```text
BLOCKED
- same config already recorded by run R-e037afb46d status=success
- D-74cadc923e: 放弃 max_value_reward 错误目标函数
  evidence_run_ids: R-e037afb46d
  reopen_condition: 只有用户明确把任务目标改成奖励预测值变大时才允许重开。
```

## 运行中发现并修正的问题

问题：十轮快速执行时，第 5 到第 10 轮在同一秒内完成，旧版 handoff 只按秒级 `ended_at` 排序，导致 `latest_successful_run_id` 错误地指向第 5 轮 `R-c222ca947b`。

修正：时间戳改为微秒级；当已有历史数据存在相同时间戳时，最新 run 查询增加数据库插入顺序作为并列排序。回归测试是 `test_handoff_uses_newest_success_when_runs_share_timestamp`。

修正后 `handoffs/latest_handoff.md` 指向第 10 轮 `R-9723365f8f`。
