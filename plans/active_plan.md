# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前实施阶段

- 最小可用版本：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff。

## 下一步

1. 使用 `python3 -m auto_iteration.cli init` 初始化目标算法仓库。
2. 每次实验前运行 `route check`。
3. 每次实验后运行 `run finish` 和 `decision add`。
4. 会话结束前运行 `handoff generate`。

