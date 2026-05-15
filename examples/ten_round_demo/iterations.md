# Ten Round Demo Iteration Plan

目标：用公式 `预测值 = weight * x + offset` 拟合固定数据 `目标值 = 2.0 * x + 1.5`，让 `mean_absolute_error`（平均绝对误差，单位是目标值单位）降到 `0.0`。

第 6 轮故意偏离设计：把 `objective` 从 `minimize_error`（最小化误差）改成 `max_value_reward`（奖励预测值变大）。这会让误差变差，随后必须记录为 `rejected`（已证伪，不应重复）并用 `route check` 拦截。

```text
round  config file     intent
01     round01.json    baseline, weight too low and offset too low
02     round02.json    increase weight
03     round03.json    increase weight again
04     round04.json    overshoot weight to observe residual pattern
05     round05.json    correct weight but offset still missing
06     round06.json    intentionally wrong objective, should be rejected
07     round07.json    return to minimize_error and raise offset
08     round08.json    raise offset again
09     round09.json    fine tune offset near target
10     round10.json    target config, should reach zero error
```

