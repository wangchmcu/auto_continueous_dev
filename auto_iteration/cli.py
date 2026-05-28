from __future__ import annotations

import argparse
import math
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


AIT_STATE_DIR = ".auto_iter"
DB_PATH = Path("state") / "agent_state.db"
SINGLE_DIR_LAYOUT = "single-dir"
LEGACY_LAYOUT = "legacy"
TOOL_ROOT = Path(__file__).resolve().parents[1]
DECISION_STATUSES = {"active", "rejected", "superseded", "open"}
RUN_STATUSES = {"running", "success", "failed", "aborted"}
TOPIC_STATUSES = {"active", "archived_open", "archived_satisfied"}
TOPIC_EVIDENCE_TYPES = {"run", "decision", "artifact"}
TOPIC_TASK_STATUSES = {"todo", "doing", "done", "blocked", "dropped"}
RULE_SOURCE_KINDS = {"user_stated", "derived", "implemented"}
RULE_KINDS = {"entry", "exit", "add", "protection", "execution", "acceptance", "recording"}
RULE_SCOPE_KINDS = {"global", "project", "topic"}
RULE_STATUSES = {"active", "superseded", "deprecated", "draft"}
PROJECT_TOPIC_RELATIONS = {"implements", "explores", "blocks", "related"}
SEARCH_FUSION_K = 60
INSTALLED_SKILLS = ["auto-iteration-entry", "auto-it-self-improve"]
TOPIC_ID_ENV_VAR = "AUTO_ITER_TOPIC_ID"
PROJECT_STATE_DIRS = [
    ("state", "SQLite state database for runs, decisions, route checks, and handoffs"),
    ("plans", "planning documents such as global, active, and version plans"),
    ("topics", "active and archived topic projections for on-demand context loading"),
    ("raw_input", "original input materials and imported old project notes"),
    ("decisions", "readable decision projections validated against the SQLite state database"),
    ("rules", "readable rule projections and current effective rule snapshot"),
    ("runs", "experiment run summaries, logs, metrics, and artifacts"),
    ("handoffs", "session handoff documents for context recovery"),
]
ACTIVE_PLAN_TEMPLATE = """# Active Plan

## 当前目标

- 使用 Codex 长周期算法迭代的本地状态闭环，并保持 tracking 信息优先于原始输入材料。

## 当前版本

- 当前版本：v0.8。
- v0.1 已完成：本地状态闭环、实验日志、结论记录和 handoff。
- v0.2 已完成：Codex 入口 skill 和 `auto-iter` 短命令。
- v0.3 已完成：`raw_input/` 读取边界和 handoff 完整性校验。
- v0.4 已完成：参数空间路线拦截、上下文标题索引和按需读取。
- v0.5 已完成：用自然语言短句触发 session 结束、session 接力和细节查阅流程。
- v0.6 已完成：`auto it self improve` 系统改进沉淀能力。
- v0.7 已完成：intent checkpoint（意图检查点），用于在计划、执行、结果和结束阶段提示 agent 先做安全检查。
- v0.8 已完成：中途记录黑盒入口，用户只说“中途记录一下”时，agent 保存当前接力点但不默认提交推送。

## 下一步

1. 用户说“中途记录一下”“先保存当前状态”“做个阶段记录”等短句时，agent 运行 `auto-iter checkpoint save --text "<用户原话>"`，内部完成 `auto-iter handoff generate` 和 `auto-iter handoff validate` 对应的保存与校验。
2. 中途记录和 session 结束使用相同的状态保存范围；区别是中途记录不默认结束会话、不默认提交、不默认推送。
3. 当用户话语像是在进入计划、执行、结果或结束阶段时，agent 先运行 `auto-iter intent check --text "<用户原话>"`。
4. 用户明确说 `auto it self improve` 时，agent 才运行系统改进沉淀流程。
5. 若 tracking 信息规模明显变大，再评估语义检索。
"""

VERSION_ITERATIONS_TEMPLATE = """# Version Iteration Tracking

## 说明

这个文件记录每次版本迭代的目标、任务状态、验收证据、后续方向，以及当前版本整体距离 `global plan` 的差距。`global plan` 的定义和完整清单在 `plans/global_plan.md`。

- `pending` 表示还没开始。
- `in_progress` 表示正在做。
- `done` 表示已经完成并有证据。
- `blocked` 表示被外部条件卡住。
- `deferred` 表示明确放到后续版本。

## 全局方案方向

- 详见 `plans/global_plan.md`。

## 当前版本

- current_version: v0.8
- status: done
- goal: 完成中途记录黑盒入口，让用户不用指明内部文件或命令也能保存当前接力点。

## v0.1 任务清单

- [x] 初始化目录：`state/`、`runs/`、`handoffs/`、`decisions/`、`plans/`。
- [x] 初始化 SQLite 数据库：记录 runs、metrics、artifacts、decisions、handoffs、route_checks。
- [x] 记录实验开始：`run start` 写入配置、数据集、命令、Git commit 和 Git branch。
- [x] 记录实验结束：`run finish` 写入状态、指标和工件路径。
- [x] 查询实验：`run list` 和 `run show`。
- [x] 记录结论：`decision add` 写入 active、rejected、superseded、open 状态。
- [x] 替代旧结论：`decision supersede` 把旧结论移动到 superseded。
- [x] 阻断重复路线：`route check` 检查重复配置以及 rejected/superseded 关键词。
- [x] 生成交接：`handoff generate` 生成 `handoffs/latest_handoff.md`。
- [x] 恢复交接：`resume` 输出下一轮应该先读的 handoff。
- [x] Codex Stop hook：`.codex/hooks.json` 调用 handoff 生成命令。
- [x] Codex skill：`skills/auto-iteration/SKILL.md` 记录使用流程。
- [x] 十轮 demo：验证从多轮实验到结论沉淀的闭环。
- [x] 版本任务跟踪：每个版本都有任务状态、验收证据和下一步方向。
- [x] handoff 接入版本任务跟踪：新 session 能看到当前版本和下一步工程任务。
- [x] 结束汇报规则：每次任务结束前报告当前版本号、本次完成项、当前版本内部剩余项、当前版本整体距离 `global plan` 的差距。
- [x] 日志摘要：自动生成 `runs/<run_id>/summary.md` 和 `runs/<run_id>/logs/error_summary.md`。
- [x] 实验命令封装：自动执行命令并捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。

## v0.1 距离 global plan

v0.1 的定位是打底版本：先让实验事实、结论、计划和 handoff 有固定落点。它不是完整的 `global plan`。

v0.1 已覆盖的全局能力：

- 账本层基础：SQLite 已记录 run、metric、artifact、decision、handoff、route check。
- 叙事层基础：`decisions/`、`handoffs/`、`plans/` 已有固定入口。
- 流程层基础：`AGENTS.md`、skill、Stop hook 已有固定规则。
- 重复路线拦截基础：能按配置哈希和 rejected/superseded 关键词阻断明显重复路线。
- 日志分级基础：每个 run 已有 `summary.md` 和 `logs/error_summary.md`，原始 stdout/stderr/debug 日志保留在 `logs/` 下。
- 实验执行基础：`run exec` 能执行单条实验命令并自动写入状态库和日志文件。

v0.1 之后仍未覆盖的全局能力：

- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 可选的语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.1 验收标准

1. `python3 -m auto_iteration.cli doctor` 通过。
2. `python3 -Wd -m unittest discover -s tests -v` 通过。
3. `handoffs/latest_handoff.md` 包含版本任务跟踪文件路径。
4. `plans/version_iterations.md` 明确列出当前版本状态、已完成任务、未完成任务和后续版本方向。

## v0.2 任务清单

- [x] 提供可安装的短命令入口 `auto-iter`。
- [x] 新增 Codex 入口 skill：`skills/auto-iteration-entry/SKILL.md`。
- [x] 入口 skill 指导 agent 在任务开始、实验前、实验后、任务结束时自动调用 `auto-iter`。
- [x] 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- [x] 提供端到端演示：测试覆盖 doctor、resume、route check、run exec、decision add、handoff generate。

## v0.2 距离 global plan

v0.2 覆盖了 Codex 入口能力：用户可以在 Codex CLI 内表达任务，agent 通过入口 skill 在同一会话内调用 `auto-iter`。

v0.2 已覆盖的全局能力：

- Codex 入口 skill：`auto-iteration-entry`。
- 短命令入口：`auto-iter`。
- 入口流程：doctor、resume、route check、run exec、decision add、handoff generate。
- 端到端演示：临时项目中通过已安装 `auto-iter` 完成完整流程。

v0.2 之后仍未覆盖的全局能力：

- raw_input 原始输入目录的读取边界和沉淀规则。
- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.3 任务清单

- [x] `init` 创建 `raw_input/`。
- [x] `AGENTS.md` 和入口 skill 明确 `raw_input/` 只能在初次开始项目或明确缺失信息时读取。
- [x] 从 `raw_input/` 找到的新信息必须沉淀回 tracking 信息。
- [x] 增加 `handoff validate`，检查 handoff 关键章节和路径。

## v0.3 距离 global plan

v0.3 覆盖了 raw_input 使用边界和 handoff 完整性校验。

v0.3 已覆盖的全局能力：

- `raw_input/` 固定目录和默认不读取规则。
- `raw_input/` 显式读取许可：初次开始项目或缺失信息检索。
- handoff 校验：关键章节、global plan、version tracking、active plan 路径。

v0.3 之后仍未覆盖的全局能力：

- 更强的路线关系管理。
- 按标题索引动态载入上下文。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.4 任务清单

- [x] 增加 `--route-relation parameter-space` 和 `--route-param name:min:max`。
- [x] `route check` 能阻断被 rejected decision 覆盖的数值参数区间。
- [x] 增加 `context index`，默认索引 plans、handoff、decisions、run summaries、error summaries。
- [x] `context index` 默认排除 `raw_input/`。
- [x] 增加 `context show --path <file> --heading "<heading>"`，按标题载入单个章节。
- [x] 读取 `raw_input/` 需要显式 `--include-raw-input` 或 `--allow-raw-input`。

## v0.4 距离 global plan

v0.4 覆盖了路线关系增强和动态上下文载入。

v0.4 已覆盖的全局能力：

- 参数空间级 rejected route 阻断。
- 标题索引读取。
- 按需载入单个 Markdown 章节。
- raw_input 默认排除。

v0.4 之后仍未覆盖的全局能力：

- 自然语言接力入口：用户只说结束 session、继续项目、查阅细节，agent 自动调用固定命令序列。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.5 任务清单

- [x] 在 `auto-iteration-entry` skill 中增加自然语言触发短句。
- [x] “结束当前 session”触发 handoff 生成、handoff 校验，并按任务需要提交推送。
- [x] “继续这个 auto-iteration 项目”触发 doctor、resume、context index 和固定读取顺序。
- [x] “查阅某个结论或实验细节”触发上下文索引，然后按需读取具体章节。
- [x] README 增加好例子：如何结束 session、如何开启新 session、如何查阅细节。
- [x] README 和 entry skill 明确 `auto-iteration` 是固定工具名，不随算法项目名称变化。
- [x] 初始化模板同步到 v0.5。

## v0.5 距离 global plan

v0.5 覆盖了自然语言接力入口和细节读取入口。

v0.5 已覆盖的全局能力：

- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 的具体命令。
- session 结束、session 接力、细节查阅都有自然语言触发短句。
- Codex entry skill 明确这些短句对应的 agent 行为。
- README 提供假设场景下的好例子。

v0.5 之后仍未覆盖的全局能力：

- `auto it self improve` 系统改进沉淀能力：用户明确调用后，从具体对话问题中抽取通用改进并更新系统。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.6 任务清单

- status: done
- goal: 完成 `auto it self improve` 系统改进沉淀能力的入口、抽象流程、落点选择和防污染检查。
- [x] 新增 `auto-it-self-improve` skill，让 `auto it self improve` 成为明确触发短句，而不是自动后台行为。
- [x] 定义抽象流程：具体问题复盘、通用问题抽取、改进落点选择、候选补丁生成、验证、提交。
- [x] 定义文件落点选择规则：根据问题类型选择 `AGENTS.md`、README、entry skill、workflow skill、CLI 命令、初始化模板、测试、plans 或 handoff 模板。
- [x] 定义禁止写入内容：具体项目名、具体数据集、一次性参数、临时路径、只对单次对话成立的细节。
- [x] 定义可写入内容：通用流程规则、触发语句、文件选择规则、测试覆盖、文档示例、CLI 或模板缺口。
- [x] 增加检查清单：每次执行都要说明抽象依据、改动文件、验证方式、被排除的具体细节。
- [x] 安装流程同步安装 `auto-it-self-improve` skill，并用测试覆盖。
- [x] 安装后自检 `python3`、`auto-iter` 命令和必要 skills 是否 ready。

## v0.6 距离 global plan

v0.6 覆盖了 `auto it self improve` 系统改进沉淀能力。

v0.6 已覆盖的全局能力：

- 用户通过明确关键字触发系统改进沉淀。
- agent 能把具体对话问题抽象成通用能力改进。
- agent 能判断改进应该落在哪些系统文件中。
- 系统有防污染检查，避免把具体项目细节写进通用规则。
- 安装流程能检查必要依赖、命令和 skills 是否 ready。

v0.6 之后仍未覆盖的全局能力：

- intent checkpoint（意图检查点）：用户说“更新计划”“执行吧”“拿到结果了”等阶段切换短句时，agent 先检查是否需要更新计划、route check、run exec、decision add 或 handoff。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.7 任务清单

- status: done
- goal: 完成自然语言阶段切换的 intent checkpoint（意图检查点）。
- [x] 新增 `auto-iter intent check --text "<用户原话>"`，识别计划、执行前、结果后、session 结束四类阶段。
- [x] `intent check` 输出 agent 下一步检查清单，但不直接写数据库、不直接运行实验。
- [x] 入口 skill 和 workflow skill 明确：用户说“做个计划”“更新计划”“执行吧”“实施吧”“确定执行”“拿到结果了”“跑完数据了”“测试结束了”等相似短句时，agent 先运行 `intent check`。
- [x] README 增加使用场景和好例子，说明用户不用记命令，agent 在 Codex CLI 内调用。
- [x] 初始化模板、当前计划和版本跟踪同步到 v0.7。
- [x] 用测试覆盖 `intent check` 输出和模板版本更新。

## v0.7 距离 global plan

v0.7 覆盖了自然语言阶段切换的安全检查入口。

v0.7 已覆盖的全局能力：

- 计划阶段：提醒 agent 检查 `plans/active_plan.md`、`plans/version_iterations.md` 和必要的 `plans/global_plan.md`。
- 执行前阶段：提醒 agent 在实验路线前运行 `auto-iter route check`，并只在命令、配置、数据、指标和工件明确时使用 `auto-iter run exec`。
- 结果后阶段：提醒 agent 收集 metrics 和 artifact，再用有证据的 `run_id` 写 decision。
- session 结束阶段：提醒 agent 生成并校验 handoff，按用户要求提交和推送。

v0.7 之后仍未覆盖的全局能力：

- 中途记录黑盒入口：用户只说“中途记录一下”时，agent 使用和 session 结束相同的状态保存范围，但不默认提交推送。
- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## v0.8 任务清单

- status: done
- goal: 完成中途记录黑盒入口。
- [x] 新增 `auto-iter checkpoint save --text "<用户原话>"`，用于生成并校验当前接力点。
- [x] 明确中途记录和 session 结束使用相同的状态保存范围；区别是中途记录不默认结束会话、不默认提交、不默认推送。
- [x] `intent check` 能识别“中途记录一下”“先保存当前状态”“做个阶段记录”等短句，并提示 agent 调用 checkpoint save。
- [x] 更新 entry skill、workflow skill、README、AGENTS 和初始化模板，让用户侧入口保持黑盒。
- [x] 用测试覆盖 checkpoint save、意图识别和 v0.8 模板。

## v0.8 距离 global plan

v0.8 覆盖了中途主动记录的黑盒入口。

v0.8 已覆盖的全局能力：

- 用户不需要知道 `active_plan`、`version_iterations`、decision、handoff 等内部落点。
- 用户可以只说“中途记录一下”，agent 在同一个 Codex session 内保存当前接力点。
- 中途记录默认不提交、不推送，只有用户明确要求提交或推送时才执行 git 操作。

v0.8 之后仍未覆盖的全局能力：

- 后续可选：语义检索。当 decision、handoff、retrospective 数量变多后再评估是否加入。

## 后续版本方向

### v0.2

- done：Codex 入口能力已完成。

### v0.3

- done：raw_input 使用边界和 handoff 校验已完成。

### v0.4

- done：路线关系增强和动态载入上下文已完成。

### v0.5

- done：自然语言接力入口和细节读取入口已完成。

### v0.6

- done：`auto it self improve` 系统改进沉淀能力。

### v0.7

- done：intent checkpoint（意图检查点），用于自然语言阶段切换前的安全检查。

### v0.8

- done：中途记录黑盒入口。

### 后续可选

- 在 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
"""

GLOBAL_PLAN_TEMPLATE = """# Global Plan

## 定义

`global plan` 指整个长周期算法迭代上下文管理方案。它不是某一个版本，也不是单个 skill；它的目标是让 Codex agent 在长周期实验中能恢复状态、避免重复路线、保存证据、生成交接，并在 Codex CLI 会话内主动调用本地工具。

## 总体形态

最终形态是轻量本地编排系统加 Codex 入口能力。

- 轻量本地编排系统：`auto_iteration` 负责写 SQLite、记录 runs、记录 decisions、保存 logs、生成 summaries、生成 handoff。
- Codex 入口能力：Codex agent 在会话内知道何时调用 `auto-iter`，用户不需要退出 Codex CLI，也不需要每次手写绝对路径。

## 全局能力清单

### 1. 状态账本

- 记录 run、config、dataset、command、git commit、git branch。
- 记录 metrics 和 artifacts。
- 记录 run 状态：running、success、failed、aborted。
- 每个实验都有 `run_id`。

### 2. 日志和摘要

- 捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。
- 生成 `summary.md`。
- 生成 `logs/error_summary.md`。
- 默认读取 summary 和 error_summary；只有调查具体失败时才读原始日志。

### 3. 结论和路线控制

- 记录 active、rejected、superseded、open 状态的 decision。
- 每个 decision 必须有 evidence run IDs。
- 新路线前运行 route check。
- 阻止明显重复配置和 rejected/superseded 路线。
- 支持参数空间被部分否定后的 route check 拦截。
- 后续可继续增强方法被替代和重开条件提示。

### 4. 交接和恢复

- 自动生成 `handoffs/latest_handoff.md`。
- handoff 指向 run summaries、decisions、plans，而不是粘贴完整原始日志。
- 新 Codex session 先读 handoff、global plan、version tracking、active plan；项目根目录存在 `AGENTS.md` 时才把它作为项目级 Codex 规则入口读取。
- 已增加 handoff 完整性校验，检查关键字段缺失。

### 5. 原始输入目录

- 每个项目开发目录可以有 `raw_input/`，用于存放原始输入材料或老项目导入材料。
- `raw_input/` 只在两种情况下读取：初次开始项目；后续开发中明确需要到原始输入里检索缺失信息。
- 正常迭代时应优先读取 `plans/`、`handoffs/`、`decisions/`、run summaries 和 SQLite 状态库。
- 理论上，工作 tracking 信息应该已经吸收并更新了 `raw_input/` 中的重要信息；如果二者冲突，默认以 tracking 信息为准，除非用户明确要求回到原始输入核对。
- 从 `raw_input/` 找到的新信息，必须沉淀回 `plans/`、`decisions/`、handoff 或 run summary，避免下次再次回查原始材料。

### 6. Codex 入口能力

- 提供 Codex 入口 skill：告诉 agent 什么时候调用 `auto-iter doctor`、`auto-iter resume`、`auto-iter route check`、`auto-iter run exec`、`auto-iter decision add`、`auto-iter handoff generate`。
- 提供短命令入口 `auto-iter`，避免每次手写源码 checkout 里的工具脚本路径。
- 用户在 Codex CLI 中表达任务，agent 在同一个会话里调用命令；用户不需要退出 Codex CLI。
- 入口 skill 只负责流程触发和命令调用顺序；状态写入仍由 `auto_iteration` 完成。

### 7. 动态载入上下文

- 建立按标题索引的上下文读取方式：先读目录和摘要，需要时再读详细内容。
- handoff、decision、run summary、error summary 都应可被按需读取。
- 避免一次性把所有历史塞进上下文。

### 8. 自然语言接力入口

- 用户可以用自然语言短句触发固定流程，例如结束 session、恢复 session、查阅某个历史细节。
- Codex entry skill 负责把这些短句映射到 `auto-iter` 命令序列。
- 用户不需要记住 `doctor`、`resume`、`context index`、`context show` 等具体命令。

### 9. Auto It Self Improve（系统改进沉淀能力）

- `auto it self improve` 是固定触发短句和能力名，指 auto_iteration 的系统改进沉淀能力：用户和 agent 解决了一个具体使用问题后，agent 把这个问题抽象成通用能力改进，并更新到 auto_iteration 系统中。
- 这个能力不能自动触发，只能在用户明确点名 `auto it self improve` 或 `auto-it-self-improve` skill 名时触发。
- 输入是已解决的对话片段、相关文件改动、失败现象和最终处理方式；输出是对 auto_iteration 系统的通用改进建议或补丁。
- 改进落点由 agent 根据问题类型选择，例如 `AGENTS.md`、README、entry skill、workflow skill、CLI 命令、初始化模板、测试、plans 或 handoff 模板。
- 必须先抽象成通用规则，再写入系统；不得把具体项目名称、具体数据集、一次性参数、临时文件路径或用户当次私有场景直接写成系统规则。
- 每次执行都应说明“具体问题是什么”“抽象后的通用问题是什么”“为什么应该改这些文件”“哪些具体细节没有写入系统”。

### 10. Intent Checkpoint（意图检查点）

- Intent checkpoint（意图检查点）指：用户话语像是在进入计划、执行前、结果后或 session 结束阶段时，agent 先运行检查命令获取下一步清单。
- 该能力的目标是减少漏记计划、漏做 route check、漏写 decision、漏生成 handoff，而不是自动替代 agent 判断。
- `auto-iter intent check --text "<用户原话>"` 只输出检查清单；它不直接写 SQLite、不启动实验、不生成结论。
- Codex entry skill 负责在用户说“做个计划”“更新计划”“执行吧”“实施吧”“确定执行”“拿到结果了”“跑完数据了”“测试结束了”“结束当前 session”等相似短句时调用该命令。
- 检查结果必须继续落回现有明确流程：计划文件、`route check`、`run exec`、`decision add`、`handoff generate` 和 `handoff validate`。

### 11. 中途记录黑盒入口

- 中途记录黑盒入口指：用户在对话中只说“中途记录一下”“先保存当前状态”“做个阶段记录”等自然语言短句，agent 自动保存当前接力点。
- 这个入口和 session 结束使用相同的状态保存范围：检查当前计划、实验事实、结论和 handoff 是否需要更新，并生成可恢复的 handoff。
- 它和 session 结束的区别是：中途记录不表示当前 session 结束，不默认提交，不默认推送。
- `auto-iter checkpoint save --text "<用户原话>"` 是 agent 内部使用的命令；用户不需要记住它。
- 如果用户同时明确要求“提交”或“推送”，agent 才在 checkpoint 后执行对应 git 操作。

### 12. 后续可选语义检索

- 当 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
- 语义检索只能作为补充入口，不能替代 SQLite、plans 和 handoff 的明确证据链。

## 版本路线

### v0.1：本地状态闭环

状态：done。

范围：

- SQLite 状态库。
- run、metric、artifact、decision、handoff、route check。
- `run exec` 执行命令并捕获日志。
- run summary 和 error summary。
- version task tracking。

### v0.2：Codex 入口能力

状态：done。

目标：用户在 Codex CLI 内只表达任务，Codex agent 根据入口 skill 自动调用 `auto-iter`，不需要用户退出 Codex 或手写绝对路径。

任务：

- 提供可安装的短命令入口 `auto-iter`。
- 新增或调整 Codex 入口 skill，让 agent 在任务开始、实验前、实验后、任务结束时自动调用对应命令。
- 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- 提供一次端到端演示：从 Codex 会话内恢复状态、route check、run exec、decision add、handoff generate。

### v0.3：raw_input 使用边界和 handoff 校验

状态：done。

目标：让原始输入材料有固定落点和明确读取边界，同时减少交接字段缺失。

任务：

- `init` 创建 `raw_input/`。
- `AGENTS.md` 和入口 skill 明确 `raw_input/` 只能在初次开始项目或明确缺失信息时读取。
- 从 `raw_input/` 找到的新信息必须沉淀回 tracking 信息。
- 增加 handoff 完整性校验。

### v0.4：路线关系增强和动态载入上下文

状态：done。

目标：减少重复路线误判，并按标题索引和摘要读取历史，减少 token 占用。

任务：

- 记录路线关系字段，并落地参数空间被部分否定后的 route check 拦截。
- 保留 reopen condition 输出；方法替代的自动判断后续可继续增强。
- 建立 handoff、decision、run summary 的标题索引。
- 先读目录和摘要，需要时再读详细内容。

### v0.5：自然语言接力入口和细节读取入口

状态：done。

目标：用户不需要记具体命令，只用自然语言短句让 Codex agent 完成 session 结束、session 接力和历史细节查阅。

任务：

- 在 Codex entry skill 中写明自然语言触发短句和对应动作。
- session 结束短句触发 handoff 生成、handoff 校验，以及按任务需要提交推送。
- session 接力短句触发 doctor、resume、context index 和固定读取顺序。
- 细节查阅短句触发 context index，然后由 agent 选择合适的文件和标题运行 context show。
- README 和 entry skill 明确 `auto-iteration` 是固定工具名，不随算法项目名称变化。
- README 添加好例子，说明如何结束 session、如何开启新 session、如何查阅某个细节。

### v0.6：auto it self improve 系统改进沉淀能力

状态：done。

目标：用户明确调用 `auto it self improve` 后，agent 能从已经解决的具体问题中抽取通用改进，并把改进落到 auto_iteration 系统合适的位置。

任务：

- 新增 `auto-it-self-improve` skill，让 `auto it self improve` 成为明确触发短句，而不是自动后台行为。
- 定义抽象流程：具体问题复盘、通用问题抽取、改进落点选择、候选补丁生成、验证、提交。
- 定义禁止写入的内容：具体项目名、具体数据集、一次性参数、临时路径、只对单次对话成立的细节。
- 定义可写入的内容：通用流程规则、触发语句、文件选择规则、测试覆盖、文档示例、CLI 或模板缺口。
- 增加检查清单，要求每次执行都说明抽象依据和被排除的具体细节。
- 安装流程同步安装 `auto-it-self-improve` skill，并用测试覆盖。
- 安装后自检 `python3`、`auto-iter` 命令和必要 skills 是否 ready。

### v0.7：intent checkpoint 意图检查点

状态：done。

目标：用户用自然语言进入计划、执行、结果或结束阶段时，agent 先得到检查清单，再决定是否更新计划、检查路线、记录实验、记录结论或生成 handoff。

任务：

- 新增 `auto-iter intent check --text "<用户原话>"`。
- 支持计划、执行前、结果后、session 结束四类阶段提示。
- 明确该命令只输出检查清单，不直接写状态、不直接运行实验。
- 更新 entry skill、workflow skill、README、AGENTS 和初始化模板。
- 用测试覆盖命令输出和 v0.7 模板。

### v0.8：中途记录黑盒入口

状态：done。

目标：用户在长对话中可以只说“中途记录一下”，agent 使用和 session 结束相同的状态保存范围保存当前接力点，但不默认提交或推送。

任务：

- 新增 `auto-iter checkpoint save --text "<用户原话>"`。
- 让 `intent check` 识别中途记录类短句。
- 更新 entry skill、workflow skill、README、AGENTS 和初始化模板。
- 用测试覆盖命令输出、意图识别和 v0.8 模板。

### 后续可选：语义检索

状态：deferred。

任务：

- 当 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
- 语义检索只能作为补充入口，不能替代 SQLite、plans 和 handoff 的明确证据链。
"""

LOW_ASSUMPTION_ACTIVE_PLAN_TEMPLATE = """# Active Plan

## 当前目标

- 当前业务目标：待用户定义。
- AIT 只负责建立可恢复的项目状态，不替用户发明开发路线。

## 低假设初始化

- 初始化只记录确定事实、未决问题和候选检查项。
- 正式版本路线必须来自 `user_confirmed` 的目标或后续明确决策。
- repo 观察和 agent 推断可以保留，但必须降级为候选内容。
- 如果 `raw_input/` 已有文件，它是初期输入源之一；先索引，再选择性读取，不自动整目录吞入。

## 对话中途接入

- 如果 AIT 在已有 Codex 对话中途接入，agent 应整理一次 bootstrap checkpoint。
- checkpoint 应总结已确认事实、用户目标、已暴露问题、未决问题和候选事项。
- 不应把完整聊天记录当作事实库；agent 应将对话压缩为结构化 tracking 信息。

## 来源标注

- `user_confirmed`：用户明确确认。
- `repo_observed`：从仓库文件或命令输出观察到。
- `raw_input_source`：从 `raw_input/` 原始材料选择性读取后沉淀。
- `conversation_summary`：agent 对当前对话的结构化摘要。
- `agent_inferred`：agent 推断，不能进入正式路线。
- `proposed_not_accepted`：候选建议，尚未被用户接受。

## candidate_checks

- 暂无已确认检查项。
- 后续 agent 可添加候选项，但必须标注 `agent_inferred` 或 `proposed_not_accepted`，直到用户确认。
"""

LOW_ASSUMPTION_VERSION_ITERATIONS_TEMPLATE = """# Version Iteration Tracking

## 说明

这个文件记录当前目标项目的版本级工作。初始化阶段采用低假设原则：不要把 agent 推断写成正式路线。

## 当前版本

- current_version: bootstrap-v0
- status: pending_user_plan
- goal: 初始化 AIT 状态结构，等待用户定义当前项目的业务开发方向。

## bootstrap-v0 任务清单

- [x] 创建 `state/`、`runs/`、`handoffs/`、`raw_input/`、`decisions/`、`plans/`。
- [x] 初始化 SQLite 状态库。
- [x] 创建低假设 `plans/global_plan.md`。
- [x] 创建低假设 `plans/active_plan.md`。
- [x] 创建低假设 `plans/version_iterations.md`。
- [ ] agent 运行 `context index --include-raw-input` 检查是否存在初期 raw input。
- [ ] 如果初始化发生在对话中途，agent 需要整理一次 bootstrap checkpoint。

## 正式路线准入规则

- 只有 `user_confirmed` 的目标才能成为正式版本路线。
- `repo_observed` 只能作为事实背景。
- `raw_input_source` 只能作为原始材料证据，必须沉淀成 tracking 信息后再作为后续默认上下文。
- `conversation_summary` 只能作为当前对话摘要。
- `agent_inferred` 和 `proposed_not_accepted` 只能进入候选区。
- 不要把 agent 推断写成正式路线。

## 未决问题

- 当前项目的业务开发目标尚未定义。
- 当前项目的验收标准尚未定义。
- 当前项目是否需要实验 run、decision 或 handoff 仍待用户确认。
"""

LOW_ASSUMPTION_PROJECT_PLAN_TEMPLATE = """# Project Plan

## 定义

`project plan` 描述当前目标项目自己的长期方向。初始化时采用低假设项目初始化：只建立结构，不替用户规划业务路线，也不记录 AIT 工具自身迭代任务。

## 低假设项目初始化

- `ait init` 只创建状态结构和低假设 tracking 模板。
- 初始化模板不得包含 AIT 自身版本路线。
- 初始化模板不得根据仓库 README 自动生成正式业务 roadmap。
- 候选建议必须标注来源，并保持未确认状态。

## 来源标注

- `user_confirmed`：可进入正式计划。
- `repo_observed`：事实背景，不自动成为任务。
- `conversation_summary`：中途接入时的压缩摘要。
- `agent_inferred`：推断，只能作为候选。
- `proposed_not_accepted`：建议，等待用户接受或删除。

## bootstrap checkpoint

- 如果 AIT 在已有对话中途接入，agent 应做一次 bootstrap checkpoint。
- checkpoint 的目标是把当前对话中的已确认事实、用户目标、暴露问题和未决问题写入 tracking 信息。
- 如果 `raw_input/` 中已有材料，bootstrap 应先运行 `context index --include-raw-input`，再按需用 `--allow-raw-input` 读取相关章节。
- checkpoint 不能把 agent 推断出的检查项提升为正式版本路线。

## raw_input 初期输入

- `raw_input/` 有内容时是初始化 bootstrap 的输入源；没有内容时保留为空目录。
- 不要让 `auto-iter init` 自动读取或概括整个 `raw_input/`。
- 读取 raw input 后必须标注 `raw_input_source`，并把有用信息写回 plans、decisions、handoff 或 run summaries。

## 全局能力清单

### 1. 状态账本

- 记录 run、metric、artifact、decision、handoff 和 route check。

### 2. 低假设计划

- 初始化只创建待用户定义的计划框架。
- 正式路线由用户确认或后续 evidence-backed decision 产生。

### 3. 中途接管

- 支持在项目对话中途接入 AIT。
- 支持将对话历史压缩成结构化 checkpoint。
- 支持把已存在的 `raw_input/` 作为初期输入源检查并选择性沉淀。

### 4. 上下文恢复

- 新 session 先读取 handoff、plans、decisions 和状态库。
- 默认不读取 raw_input，除非是初始导入或明确缺失信息查询。
"""

LOW_ASSUMPTION_PROJECT_RECORD_RULES_TEMPLATE = """# Project Record Rules

## 定义

`project record rules` 描述当前项目如何定制使用 AIT 记录系统。它不是项目知识库，也不是 AIT 通用说明。

## 默认规则

- 当前项目暂未定义项目定制规则。
- 本文件只记录项目级记录流程定制，例如本项目是否要求特定证据链、恢复入口或 topic 绑定方式。
- 本文件不能记录 AIT 工具自身功能迭代任务；AIT update、migrate、search、handoff、skill 等工具改动应进入 AIT source repository 的计划。
- 本文件不记录代码坑点或技术结论；这些应进入 topic evidence、decision、handoff、run summary 或具体 topic plan。
"""

GLOBAL_PLAN_COMPAT_TEMPLATE = """# Global Plan

## Compatibility Entry

This file is a compatibility entry for older AIT workflows that still look for `plans/global_plan.md`.

Current project planning lives in:

- `plans/project_plan.md`
- `plans/project_record_rules.md`

AIT 工具自身迭代任务不能写入被接管项目。若需求对象是 AIT、auto-iter、update、migrate、search、handoff 或 skill，请切到 AIT source repository，并更新 AIT 自己的 global plan、version tracking 或 topic plan。
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def state_root_for_project(project_root: Path, prefer_legacy: bool = False) -> Path:
    if (project_root / AIT_STATE_DIR / DB_PATH).exists():
        return project_root / AIT_STATE_DIR
    if (project_root / DB_PATH).exists():
        return project_root
    return project_root if prefer_legacy else project_root / AIT_STATE_DIR


def root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if candidate.name == AIT_STATE_DIR and (candidate / DB_PATH).exists():
            return candidate.parent
        if (candidate / AIT_STATE_DIR / DB_PATH).exists():
            return candidate
        if (candidate / DB_PATH).exists():
            return candidate
    return cwd


def state_root(prefer_legacy: bool = False) -> Path:
    return state_root_for_project(root(), prefer_legacy=prefer_legacy)


def state_path(*parts: str | Path, prefer_legacy: bool = False) -> Path:
    path = state_root(prefer_legacy=prefer_legacy)
    for part in parts:
        path /= part
    return path


def project_layout() -> str:
    return SINGLE_DIR_LAYOUT if state_root() != root() else LEGACY_LAYOUT


def db_path(prefer_legacy: bool = False) -> Path:
    return state_path(DB_PATH, prefer_legacy=prefer_legacy)


def has_project_state() -> bool:
    project_root = root()
    return (project_root / AIT_STATE_DIR / DB_PATH).exists() or (project_root / DB_PATH).exists()


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise UserError("state database does not exist; run `auto-iteration init` first")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def database(require_existing: bool = True, prefer_legacy: bool = False) -> sqlite3.Connection:
    if require_existing:
        db = connect()
    else:
        db = sqlite3.connect(db_path(prefer_legacy=prefer_legacy))
        db.row_factory = sqlite3.Row
    init_schema(db)
    try:
        yield db
        db.commit()
    finally:
        db.close()


class UserError(Exception):
    pass


def read_json(path: str | Path) -> Any:
    resolved = Path(path).expanduser().resolve()
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UserError(f"file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise UserError(f"invalid JSON in {resolved}: {exc}") from exc


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_data(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_dir(run_id: str) -> Path:
    return state_path("runs", run_id)


def logs_dir(run_id: str) -> Path:
    return run_dir(run_id) / "logs"


def git_value(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root(),
            text=True,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def git_commit() -> str:
    return git_value(["rev-parse", "HEAD"])


def git_branch() -> str:
    return git_value(["branch", "--show-current"])


def ensure_dirs(prefer_legacy: bool = False) -> None:
    for path in [
        "state",
        "runs",
        "handoffs/archive",
        "topics/archive",
        "raw_input",
        "decisions/active",
        "decisions/rejected",
        "decisions/superseded",
        "decisions/open",
        "rules/active",
        "rules/superseded",
        "rules/deprecated",
        "rules/draft",
        "plans",
    ]:
        state_path(path, prefer_legacy=prefer_legacy).mkdir(parents=True, exist_ok=True)


def write_if_missing(path: Path, text: str) -> None:
    if not path.exists():
        path.write_text(text.rstrip() + "\n", encoding="utf-8")


def ensure_plan_files(prefer_legacy: bool = False) -> None:
    write_if_missing(state_path("plans", "project_plan.md", prefer_legacy=prefer_legacy), LOW_ASSUMPTION_PROJECT_PLAN_TEMPLATE)
    write_if_missing(
        state_path("plans", "project_record_rules.md", prefer_legacy=prefer_legacy),
        LOW_ASSUMPTION_PROJECT_RECORD_RULES_TEMPLATE,
    )
    write_if_missing(state_path("plans", "global_plan.md", prefer_legacy=prefer_legacy), GLOBAL_PLAN_COMPAT_TEMPLATE)
    write_if_missing(state_path("plans", "active_plan.md", prefer_legacy=prefer_legacy), LOW_ASSUMPTION_ACTIVE_PLAN_TEMPLATE)
    write_if_missing(
        state_path("plans", "version_iterations.md", prefer_legacy=prefer_legacy),
        LOW_ASSUMPTION_VERSION_ITERATIONS_TEMPLATE,
    )


def is_global_plan_compat(text: str) -> bool:
    return "Compatibility Entry" in text and "plans/project_plan.md" in text


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{stamp}_{index}{path.suffix}")
        index += 1
    return candidate


def migrate_project_plan_files() -> dict[str, str]:
    plans = state_path("plans")
    plans.mkdir(parents=True, exist_ok=True)
    project_plan = plans / "project_plan.md"
    project_record_rules = plans / "project_record_rules.md"
    global_plan = plans / "global_plan.md"
    legacy_global_plan = plans / "legacy_global_plan_before_project_plan_split.md"
    result = {
        "project_plan": str(project_plan.resolve()),
        "project_record_rules": str(project_record_rules.resolve()),
        "legacy_global_plan": "none",
        "global_plan_compat": str(global_plan.resolve()),
        "migration_note": "none",
    }
    created_project_plan = not project_plan.exists()
    created_project_record_rules = not project_record_rules.exists()
    global_text = global_plan.read_text(encoding="utf-8", errors="replace") if global_plan.exists() else None
    rewrite_global_plan = global_text is None or not is_global_plan_compat(global_text)
    write_if_missing(project_plan, LOW_ASSUMPTION_PROJECT_PLAN_TEMPLATE)
    write_if_missing(project_record_rules, LOW_ASSUMPTION_PROJECT_RECORD_RULES_TEMPLATE)
    if rewrite_global_plan:
        if global_text:
            legacy_path = unique_path(legacy_global_plan)
            legacy_path.write_text(global_text, encoding="utf-8")
            result["legacy_global_plan"] = str(legacy_path.resolve())
        global_plan.write_text(GLOBAL_PLAN_COMPAT_TEMPLATE.rstrip() + "\n", encoding="utf-8")
    changed = created_project_plan or created_project_record_rules or rewrite_global_plan
    if changed:
        note_path = unique_path(
            state_path("topics", f"migration_{datetime.now(timezone.utc).strftime('%Y%m%d')}_project_plan_split.md")
        )
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(render_project_plan_split_migration_note(result), encoding="utf-8")
        result["migration_note"] = str(note_path.resolve())
    else:
        existing_notes = sorted(state_path("topics").glob("migration_*_project_plan_split.md"))
        if existing_notes:
            result["migration_note"] = str(existing_notes[-1].resolve())
    return result


def render_project_plan_split_migration_note(result: dict[str, str]) -> str:
    topic_ids: list[str] = []
    current_db_path = db_path()
    if current_db_path.exists():
        with database() as db:
            topic_ids = [row["topic_id"] for row in db.execute("select topic_id from topics order by updated_at desc").fetchall()]
            current = active_topic(db)
    else:
        current = None
    default_topic = current["topic_id"] if current else "none"
    topic_lines = "\n".join(f"- {topic_id}" for topic_id in topic_ids) or "- none"
    return (
        "# Project Plan Split Migration\n\n"
        f"- migrated_at: {now_iso()}\n"
        f"- project_plan: {result['project_plan']}\n"
        f"- project_record_rules: {result['project_record_rules']}\n"
        f"- legacy_global_plan: {result['legacy_global_plan']}\n"
        f"- global_plan_compat: {result['global_plan_compat']}\n"
        f"- default_topic_id: {default_topic}\n\n"
        "## Recovery Entrypoints\n\n"
        f"- handoff: {state_path('handoffs', 'latest_handoff.md')}\n"
        f"- topic_index: {topic_index_path()}\n"
        f"- topic_board: {topic_board_path()}\n"
        "- topic_plan: topics/<topic_id>/plan.md\n\n"
        "## Topic IDs At Migration\n\n"
        f"{topic_lines}\n\n"
        "## Notes\n\n"
        "- This is operational migration metadata, not a project technical conclusion.\n"
        "- The legacy global plan is kept as readable history so old project detail remains searchable.\n"
        "- New project planning should use project_plan and project_record_rules; AIT tool work belongs in the AIT source repository.\n"
    )


def init_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        create table if not exists projects (
            project_id text primary key,
            root_path text not null,
            current_goal text not null default ''
        );

        create table if not exists runs (
            run_id text primary key,
            project_id text not null,
            session_id text,
            git_commit text not null,
            git_branch text not null,
            dataset_id text not null,
            seed text,
            command text not null,
            config_json text not null,
            config_hash text not null,
            status text not null,
            started_at text not null,
            ended_at text,
            summary text not null default ''
        );

        create table if not exists metrics (
            run_id text not null,
            metric_name text not null,
            metric_value real not null,
            unit text not null,
            direction text not null,
            primary key (run_id, metric_name)
        );

        create table if not exists artifacts (
            artifact_id text primary key,
            run_id text not null,
            kind text not null,
            path text not null,
            sha256 text not null,
            summary text not null default ''
        );

        create table if not exists decisions (
            decision_id text primary key,
            status text not null,
            title text not null,
            claim text not null,
            evidence_run_ids_json text not null,
            route_keywords_json text not null,
            supersedes_decision_id text,
            reopen_condition text not null default '',
            created_at text not null
        );

        create table if not exists rules (
            rule_id text primary key,
            title text not null,
            claim text not null,
            source_kind text not null,
            rule_kind text not null,
            scope_kind text not null,
            status text not null,
            supersedes_rule_id text,
            evidence_json text not null default '{"items":[],"notes":[]}',
            created_at text not null,
            updated_at text not null
        );

        create table if not exists handoffs (
            handoff_id text primary key,
            created_at text not null,
            based_on_run_id text,
            path text not null,
            handoff_md text not null
        );

        create table if not exists route_checks (
            check_id text primary key,
            created_at text not null,
            proposed_config_hash text not null,
            proposed_summary text not null,
            result text not null,
            matched_decision_ids_json text not null
        );

        create table if not exists topics (
            topic_id text primary key,
            title text not null,
            status text not null,
            summary text not null default '',
            current_goal text not null default '',
            restore_hint text not null default '',
            created_at text not null,
            updated_at text not null
        );

        create table if not exists topic_events (
            event_id text primary key,
            topic_id text not null,
            event_type text not null,
            summary text not null default '',
            created_at text not null
        );

        create table if not exists topic_evidence_links (
            topic_id text not null,
            evidence_type text not null,
            evidence_id text not null,
            summary text not null default '',
            created_at text not null,
            primary key (topic_id, evidence_type, evidence_id)
        );

        create table if not exists topic_plans (
            topic_id text primary key,
            status text not null default 'open',
            goal text not null default '',
            non_goals_json text not null default '[]',
            acceptance_json text not null default '[]',
            stop_conditions_json text not null default '[]',
            escalation_conditions_json text not null default '[]',
            updated_at text not null
        );

        create table if not exists topic_plan_items (
            item_id text primary key,
            topic_id text not null,
            status text not null,
            title text not null,
            description text not null default '',
            acceptance text not null default '',
            evidence_json text not null default '[]',
            created_at text not null,
            updated_at text not null
        );

        create table if not exists project_topic_links (
            project_heading text not null,
            topic_id text not null,
            relation text not null,
            summary text not null default '',
            created_at text not null,
            updated_at text not null,
            primary key (project_heading, topic_id, relation)
        );

        create table if not exists search_documents (
            doc_id text primary key,
            source_type text not null,
            source_id text not null default '',
            path text not null,
            heading text not null default '',
            title text not null default '',
            body text not null,
            related_ids_json text not null,
            updated_at text not null
        );

        create table if not exists search_vectors (
            doc_id text primary key,
            token_counts_json text not null,
            token_norm real not null
        );

        create table if not exists search_graph_edges (
            source_doc_id text not null,
            target_doc_id text not null,
            relation_type text not null,
            summary text not null default '',
            primary key (source_doc_id, target_doc_id, relation_type)
        );

        create table if not exists search_index_meta (
            scope text primary key,
            indexed_at text not null,
            source_signature text not null,
            doc_count integer not null,
            edge_count integer not null,
            has_fts integer not null
        );
        """
    )


def command_init(args: argparse.Namespace) -> int:
    prefer_legacy = bool(getattr(args, "legacy_layout", False))
    ensure_dirs(prefer_legacy=prefer_legacy)
    ensure_plan_files(prefer_legacy=prefer_legacy)
    with database(require_existing=False, prefer_legacy=prefer_legacy) as db:
        init_schema(db)
        project_id = hashlib.sha256(str(root()).encode("utf-8")).hexdigest()[:12]
        db.execute(
            """
            insert into projects (project_id, root_path, current_goal)
            values (?, ?, '')
            on conflict(project_id) do update set root_path = excluded.root_path
            """,
            (project_id, str(root())),
        )
        write_topic_projections(db)
        write_rule_projections(db)
    print(f"initialized {root()}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    missing = [
        name
        for name in ["state", "runs", "handoffs", "raw_input", "decisions", "plans"]
        if not state_path(name).exists()
    ]
    if missing:
        raise UserError("missing directories: " + ", ".join(missing))
    missing_files = [
        name
        for name in ["plans/active_plan.md", "plans/version_iterations.md"]
        if not state_path(name).exists()
    ]
    if not state_path("plans", "project_plan.md").exists() and not state_path("plans", "global_plan.md").exists():
        missing_files.append("plans/project_plan.md")
    if missing_files:
        raise UserError("missing plan files: " + ", ".join(missing_files))
    print("state: ok")
    with database() as db:
        row = db.execute("select count(*) from sqlite_master where type = 'table'").fetchone()
        resolution = resolve_topic_id(db, getattr(args, "topic_id", None))
    if row[0] < 7:
        raise UserError("database schema is incomplete")
    print("database: ok")
    print(f"root: {root()}")
    print(f"state_dir: {state_root()}")
    print(f"layout: {project_layout()}")
    if not state_path("plans", "project_plan.md").exists() and state_path("plans", "global_plan.md").exists():
        print("migration_hint: legacy global_plan detected; run `auto-iter migrate` to create project_plan.md")
    print(f"resolved_topic_id: {resolution.topic_id or 'none'}")
    print(f"resolved_topic_source: {resolution.source}")
    return 0


def migrate_single_dir_layout() -> dict[str, Any]:
    if project_layout() == SINGLE_DIR_LAYOUT:
        return {
            "status": "already-single-dir",
            "state_dir": str(state_root().resolve()),
            "moved": [],
            "migration_note": "none",
        }
    project_root = root()
    target = project_root / AIT_STATE_DIR
    if target.exists() and any(target.iterdir()):
        raise UserError(f"{AIT_STATE_DIR} already exists and is not empty")
    target.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for name, _description in PROJECT_STATE_DIRS:
        source = project_root / name
        destination = target / name
        if source.exists():
            shutil.move(str(source), str(destination))
            moved.append(name)
    note_path = unique_path(
        target / "topics" / f"migration_{datetime.now(timezone.utc).strftime('%Y%m%d')}_single_dir_layout.md"
    )
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(render_single_dir_layout_migration_note(project_root, target, moved), encoding="utf-8")
    return {
        "status": "migrated",
        "state_dir": str(target.resolve()),
        "moved": moved,
        "migration_note": str(note_path.resolve()),
    }


def render_single_dir_layout_migration_note(project_root: Path, target: Path, moved: list[str]) -> str:
    moved_lines = "\n".join(f"- {name}/ -> {AIT_STATE_DIR}/{name}/" for name in moved) or "- none"
    return (
        "# Single Directory Layout Migration\n\n"
        "## Summary\n\n"
        f"- migrated_at: {now_iso()}\n"
        f"- project_root: {project_root}\n"
        f"- state_dir: {target}\n"
        f"- database: {target / DB_PATH}\n\n"
        "## Moved Directories\n\n"
        f"{moved_lines}\n\n"
        "## Recovery Entrypoints\n\n"
        f"- handoff: {target / 'handoffs' / 'latest_handoff.md'}\n"
        f"- plans: {target / 'plans'}\n"
        f"- topics: {target / 'topics'}\n"
    )


def command_migrate(args: argparse.Namespace) -> int:
    if getattr(args, "layout", "project-plan") == SINGLE_DIR_LAYOUT:
        layout_migration = migrate_single_dir_layout()
        with database() as db:
            created_topic_plans = create_missing_topic_plans(db)
            write_topic_projections(db)
            current = active_topic(db)
        print("layout migration complete")
        print(f"status: {layout_migration['status']}")
        print(f"state_dir: {layout_migration['state_dir']}")
        print(f"moved: {', '.join(layout_migration['moved']) if layout_migration['moved'] else 'none'}")
        print(f"migration_note: {layout_migration['migration_note']}")
        print(f"created_topic_plans: {created_topic_plans}")
        print(f"default_topic_id: {current['topic_id'] if current else 'none'}")
        print(f"topic_board: {topic_board_path().resolve()}")
        return 0
    plan_migration = migrate_project_plan_files()
    with database() as db:
        created_topic_plans = create_missing_topic_plans(db)
        write_topic_projections(db)
        write_rule_projections(db)
        current = active_topic(db)
        rule_count = db.execute("select count(*) from rules").fetchone()[0]
    rules_snapshot = current_rules_snapshot_path().resolve()
    print("migration complete")
    print(f"project_plan: {plan_migration['project_plan']}")
    print(f"project_record_rules: {plan_migration['project_record_rules']}")
    print(f"legacy_global_plan: {plan_migration['legacy_global_plan']}")
    print(f"global_plan_compat: {plan_migration['global_plan_compat']}")
    print(f"migration_note: {plan_migration['migration_note']}")
    print(f"created_topic_plans: {created_topic_plans}")
    print(f"default_topic_id: {current['topic_id'] if current else 'none'}")
    print(f"topic_board: {topic_board_path().resolve()}")
    print(f"rules_snapshot: {rules_snapshot}")
    print(f"rule_count: {rule_count}")
    print("next_step_1: run `auto-iter doctor`")
    print(f"next_step_2: review {plan_migration['project_record_rules']}")
    print(f"next_step_3: inspect {rules_snapshot}")
    if rule_count == 0:
        print(
            "rule_migration_hint: no explicit rules recorded yet; if the project already has stable workflow "
            "rules, backfill them with `auto-iter rule add`."
        )
    return 0


def path_entries(path_text: str, platform_name: str | None = None) -> list[Any]:
    windows = is_windows_platform(platform_name)
    separator = ";" if windows else os.pathsep
    path_type = PureWindowsPath if windows else Path
    if windows:
        return [path_type(entry) for entry in path_text.split(separator) if entry]
    return [path_type(entry).expanduser() for entry in path_text.split(separator) if entry]


def is_standard_command_dir(path: Any, home: Any, platform_name: str | None = None) -> bool:
    text = str(path).replace("\\", "/").rstrip("/")
    home_text = str(home).replace("\\", "/").rstrip("/")
    if is_windows_platform(platform_name):
        return text.lower().endswith("/scripts") or text.lower().endswith("/auto-iteration/bin")
    return text.endswith("/opt/homebrew/bin") or text.endswith("/usr/local/bin") or text == f"{home_text}/.local/bin"


def recommended_bin_dir(
    platform_name: str | None = None,
    path_text: str | None = None,
    home: Any | None = None,
    environ: dict[str, str] | None = None,
    is_writable: Any | None = None,
) -> Any:
    env = os.environ if environ is None else environ
    windows = is_windows_platform(platform_name)
    path_type = PureWindowsPath if windows else Path
    resolved_home = home if home is not None else path_type(Path.home())
    current_path = path_text if path_text is not None else env.get("PATH", "")
    writable = is_writable or (lambda candidate: Path(candidate).is_dir() and os.access(candidate, os.W_OK))

    for entry in path_entries(current_path, platform_name):
        if is_standard_command_dir(entry, resolved_home, platform_name) and writable(entry):
            return entry

    if windows:
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data:
            return PureWindowsPath(local_app_data) / "Programs" / "auto-iteration" / "bin"
        return PureWindowsPath(resolved_home) / "AppData" / "Local" / "Programs" / "auto-iteration" / "bin"
    return Path(resolved_home) / ".local" / "bin"


def default_bin_dir() -> Path:
    return Path(recommended_bin_dir())


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


@dataclass(frozen=True)
class CommandWrapperSpec:
    filename: str
    text: str
    executable: bool


def is_windows_platform(platform_name: str | None = None) -> bool:
    if platform_name:
        return platform_name.lower().startswith(("win", "nt"))
    return os.name == "nt" or sys.platform.startswith("win")


def python_executable() -> str:
    return sys.executable or shutil.which("python3") or shutil.which("python") or "python"


def command_wrapper_spec(tool_path: Any, platform_name: str | None = None) -> CommandWrapperSpec:
    tool_text = str(tool_path)
    python_text = python_executable()
    if is_windows_platform(platform_name):
        return CommandWrapperSpec(
            filename="auto-iter.cmd",
            text="\r\n".join(["@echo off", f'"{python_text}" "{tool_text}" %*', ""]),
            executable=False,
        )
    return CommandWrapperSpec(
        filename="auto-iter",
        text="\n".join(
            [
                "#!/usr/bin/env sh",
                f"exec {shlex.quote(python_text)} {shlex.quote(tool_text)} \"$@\"",
                "",
            ]
        ),
        executable=True,
    )


def command_paths(bin_dir: Path) -> list[Path]:
    return [bin_dir / "auto-iter", bin_dir / "auto-iter.cmd"]


def install_artifacts(bin_dir: Path, skills_dir: Path) -> tuple[Path, list[tuple[str, Path]]]:
    bin_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    tool_path = TOOL_ROOT / "tools" / "auto_iter.py"
    wrapper = command_wrapper_spec(tool_path)
    command_path = bin_dir / wrapper.filename
    command_path.write_text(wrapper.text, encoding="utf-8")
    if wrapper.executable:
        command_path.chmod(0o755)

    print(f"installed command: {command_path}")
    installed_skills: list[tuple[str, Path]] = []
    for skill_name in INSTALLED_SKILLS:
        source_skill = TOOL_ROOT / "skills" / skill_name
        if not source_skill.exists():
            raise UserError(f"skill source does not exist: {source_skill}")
        target_skill = skills_dir / skill_name
        shutil.copytree(source_skill, target_skill, dirs_exist_ok=True)
        installed_skills.append((skill_name, target_skill))
        print(f"installed skill: {target_skill}")
    return command_path, installed_skills


def remove_installed_artifacts(bin_dir: Path, skills_dir: Path) -> None:
    removed_command = False
    for command_path in command_paths(bin_dir):
        if not command_path.exists():
            print(f"command not installed: {command_path}")
            continue
        command_text = command_path.read_text(encoding="utf-8", errors="replace")
        expected_target = str(TOOL_ROOT / "tools" / "auto_iter.py")
        if expected_target not in command_text:
            raise UserError(f"refusing to remove command not installed by this AIT checkout: {command_path}")
        command_path.unlink()
        print(f"removed command: {command_path}")
        removed_command = True
    if not removed_command:
        print("no installed command wrappers removed")

    for skill_name in INSTALLED_SKILLS:
        skill_dir = skills_dir / skill_name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            print(f"removed skill: {skill_name} ({skill_dir})")
        else:
            print(f"skill not installed: {skill_name} ({skill_dir})")


def command_install(args: argparse.Namespace) -> int:
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    command_path, installed_skills = install_artifacts(bin_dir, skills_dir)
    verify_installation(command_path, installed_skills)
    return 0


def command_uninstall(args: argparse.Namespace) -> int:
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    remove_installed_artifacts(bin_dir, skills_dir)

    remove_project_state = should_remove_project_state(args)
    if remove_project_state:
        remove_project_state_dirs()
    else:
        print("project state preserved")

    print("uninstall check: ok")
    return 0


def command_update(args: argparse.Namespace) -> int:
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    remove_installed_artifacts(bin_dir, skills_dir)
    command_path, installed_skills = install_artifacts(bin_dir, skills_dir)
    verify_installation(command_path, installed_skills)
    print("project state preserved")
    if args.check_project:
        if has_project_state():
            print("project check:")
            command_doctor(argparse.Namespace())
        else:
            print("project check skipped: no AIT project state found; init not run")
    print("update check: ok")
    return 0


def print_project_state_summary() -> None:
    print("Project state directories:")
    if project_layout() == SINGLE_DIR_LAYOUT:
        print(f"- {AIT_STATE_DIR}/: consolidated AIT project state directory")
    else:
        for name, description in PROJECT_STATE_DIRS:
            print(f"- {name}/: {description}")


def should_remove_project_state(args: argparse.Namespace) -> bool:
    print_project_state_summary()
    if args.remove_project_state:
        return True
    if args.keep_project_state:
        return False
    if sys.stdin.isatty():
        answer = input("Remove these project state directories too? [y/N] ").strip().lower()
        return answer in {"y", "yes"}
    print("non-interactive uninstall: keeping project state; pass --remove-project-state to delete it")
    return False


def remove_project_state_dirs() -> None:
    if project_layout() == SINGLE_DIR_LAYOUT:
        path = state_root()
        if path.is_dir():
            shutil.rmtree(path)
            print(f"removed project state: {AIT_STATE_DIR}")
        elif path.exists():
            path.unlink()
            print(f"removed project state: {AIT_STATE_DIR}")
        else:
            print(f"project state not found: {AIT_STATE_DIR}")
        return
    for name, _description in PROJECT_STATE_DIRS:
        path = root() / name
        if path.is_dir():
            shutil.rmtree(path)
            print(f"removed project state: {name}")
        elif path.exists():
            path.unlink()
            print(f"removed project state: {name}")
        else:
            print(f"project state not found: {name}")


def topics_dir() -> Path:
    return state_path("topics")


def rules_dir() -> Path:
    return state_path("rules")


def rule_status_dir(status: str) -> Path:
    return rules_dir() / status


def current_rules_snapshot_path() -> Path:
    return rules_dir() / "current_effective.md"


def topic_archive_dir() -> Path:
    return topics_dir() / "archive"


def topic_archive_path(topic_id: str) -> Path:
    return topic_archive_dir() / f"{topic_id}.md"


def topic_dir(topic_id: str) -> Path:
    return topics_dir() / topic_id


def topic_plan_path(topic_id: str) -> Path:
    return topic_dir(topic_id) / "plan.md"


def topic_handoff_path(topic_id: str) -> Path:
    return topic_dir(topic_id) / "latest_handoff.md"


def topic_handoff_archive_dir(topic_id: str) -> Path:
    return topic_dir(topic_id) / "handoffs" / "archive"


def default_topic_plan_path() -> Path:
    return topics_dir() / "default_topic_plan.md"


def topic_board_path() -> Path:
    return topics_dir() / "board.md"


def project_topic_links_path() -> Path:
    return state_path("plans", "project_topic_links.md")


def active_topic_path() -> Path:
    return topics_dir() / "active_topic.md"


def topic_index_path() -> Path:
    return topics_dir() / "index.md"


def active_topic(db: sqlite3.Connection) -> sqlite3.Row | None:
    return db.execute("select * from topics where status = 'active' order by updated_at desc limit 1").fetchone()


def get_topic(db: sqlite3.Connection, topic_id: str) -> sqlite3.Row:
    row = db.execute("select * from topics where topic_id = ?", (topic_id,)).fetchone()
    if not row:
        raise UserError(f"unknown topic_id: {topic_id}")
    return row


@dataclass(frozen=True)
class TopicResolution:
    topic_id: str | None
    source: str


def resolve_topic_id(db: sqlite3.Connection, topic_id: str | None = None) -> TopicResolution:
    if topic_id:
        get_topic(db, topic_id)
        return TopicResolution(topic_id=topic_id, source="argument")

    env_topic_id = os.environ.get(TOPIC_ID_ENV_VAR, "").strip()
    if env_topic_id:
        get_topic(db, env_topic_id)
        return TopicResolution(topic_id=env_topic_id, source="environment")

    default_topic = active_topic(db)
    if default_topic:
        return TopicResolution(topic_id=default_topic["topic_id"], source="default_topic")

    return TopicResolution(topic_id=None, source="none")


def open_topic_count(db: sqlite3.Connection) -> int:
    return db.execute(
        "select count(*) from topics where status in ('active', 'archived_open')"
    ).fetchone()[0]


def resolve_write_topic_id(
    db: sqlite3.Connection,
    topic_id: str | None = None,
    allow_default_topic: bool = False,
) -> TopicResolution:
    resolution = resolve_topic_id(db, topic_id)
    if not resolution.topic_id:
        raise UserError("topic_id required: pass --topic-id, set AUTO_ITER_TOPIC_ID, or create a default topic")
    if resolution.source == "default_topic" and not allow_default_topic and open_topic_count(db) > 1:
        raise UserError(
            "multiple open topics; pass --topic-id, set AUTO_ITER_TOPIC_ID, or use --allow-default-topic"
        )
    return resolution


def add_topic_event(db: sqlite3.Connection, topic_id: str, event_type: str, summary: str = "") -> None:
    db.execute(
        """
        insert into topic_events (event_id, topic_id, event_type, summary, created_at)
        values (?, ?, ?, ?, ?)
        """,
        (new_id("TE"), topic_id, event_type, summary, now_iso()),
    )


def topic_event_lines(db: sqlite3.Connection, topic_id: str) -> list[str]:
    rows = db.execute(
        "select event_type, summary, created_at from topic_events where topic_id = ? order by created_at desc, rowid desc limit 8",
        (topic_id,),
    ).fetchall()
    if not rows:
        return ["- none"]
    return [f"- {row['created_at']} {row['event_type']}: {row['summary'] or 'none'}" for row in rows]


def topic_evidence_lines(db: sqlite3.Connection, topic_id: str, limit: int = 12) -> list[str]:
    rows = db.execute(
        """
        select evidence_type, evidence_id, summary, created_at
        from topic_evidence_links
        where topic_id = ?
        order by created_at desc, rowid desc
        limit ?
        """,
        (topic_id, limit),
    ).fetchall()
    if not rows:
        return ["- none"]
    lines: list[str] = []
    for row in rows:
        detail = topic_evidence_detail(db, row["evidence_type"], row["evidence_id"])
        summary = f" summary={row['summary']}" if row["summary"] else ""
        lines.append(f"- {row['evidence_type']} {row['evidence_id']}: {detail}{summary}")
    return lines


def topic_evidence_detail(db: sqlite3.Connection, evidence_type: str, evidence_id: str) -> str:
    if evidence_type == "run":
        row = db.execute("select status, dataset_id from runs where run_id = ?", (evidence_id,)).fetchone()
        return f"status={row['status']} dataset={row['dataset_id']}" if row else "missing"
    if evidence_type == "decision":
        row = db.execute("select status, title from decisions where decision_id = ?", (evidence_id,)).fetchone()
        return f"status={row['status']} title={row['title']}" if row else "missing"
    if evidence_type == "artifact":
        row = db.execute("select kind, path from artifacts where artifact_id = ?", (evidence_id,)).fetchone()
        return f"{row['kind']} path={row['path']}" if row else "missing"
    return "unknown evidence type"


def project_heading_exists(project_heading: str) -> bool:
    path = state_path("plans", "project_plan.md")
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        marker, _, title = stripped.partition(" ")
        if marker and set(marker) == {"#"} and title.strip() == project_heading:
            return True
    return False


def project_topic_link_rows(
    db: sqlite3.Connection,
    topic_id: str | None = None,
    project_heading: str | None = None,
) -> list[sqlite3.Row]:
    conditions: list[str] = []
    params: list[str] = []
    if topic_id:
        conditions.append("project_topic_links.topic_id = ?")
        params.append(topic_id)
    if project_heading:
        conditions.append("project_topic_links.project_heading = ?")
        params.append(project_heading)
    where = " where " + " and ".join(conditions) if conditions else ""
    return db.execute(
        f"""
        select project_topic_links.*, topics.title as topic_title, topics.status as topic_status
        from project_topic_links
        join topics on topics.topic_id = project_topic_links.topic_id
        {where}
        order by project_topic_links.project_heading,
                 project_topic_links.updated_at desc,
                 project_topic_links.created_at desc
        """,
        params,
    ).fetchall()


def project_topic_link_lines(
    db: sqlite3.Connection,
    topic_id: str | None = None,
    project_heading: str | None = None,
) -> list[str]:
    rows = project_topic_link_rows(db, topic_id=topic_id, project_heading=project_heading)
    if not rows:
        return ["- none"]
    lines: list[str] = []
    for row in rows:
        summary = f" summary={row['summary']}" if row["summary"] else ""
        lines.append(
            f"- project_heading={row['project_heading']} topic_id={row['topic_id']} "
            f"relation={row['relation']} topic_title={row['topic_title']} topic_status={row['topic_status']}{summary}"
        )
    return lines


def render_project_topic_links(db: sqlite3.Connection) -> str:
    rows = project_topic_link_rows(db)
    lines = ["# Project Topic Links", ""]
    if not rows:
        lines += ["## None", "", "- none", ""]
        return "\n".join(lines)
    current_heading: str | None = None
    for row in rows:
        if row["project_heading"] != current_heading:
            current_heading = row["project_heading"]
            lines += [f"## {current_heading}", ""]
        summary = f" summary={row['summary']}" if row["summary"] else ""
        lines.append(
            f"- topic_id={row['topic_id']} relation={row['relation']} "
            f"topic_title={row['topic_title']} topic_status={row['topic_status']}{summary}"
        )
    lines.append("")
    return "\n".join(lines)


def write_project_topic_links_projection(db: sqlite3.Connection) -> None:
    rows = project_topic_link_rows(db)
    path = project_topic_links_path()
    if not rows:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_project_topic_links(db), encoding="utf-8")


def get_topic_plan(db: sqlite3.Connection, topic_id: str) -> sqlite3.Row:
    row = db.execute("select * from topic_plans where topic_id = ?", (topic_id,)).fetchone()
    if not row:
        raise UserError(f"no topic plan for topic_id: {topic_id}")
    return row


def markdown_list(items_json: str) -> list[str]:
    items = json.loads(items_json)
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def topic_task_lines(db: sqlite3.Connection, topic_id: str, status: str) -> list[str]:
    rows = db.execute(
        """
        select item_id, title, description, acceptance
        from topic_plan_items
        where topic_id = ? and status = ?
        order by updated_at desc, created_at desc
        """,
        (topic_id, status),
    ).fetchall()
    if not rows:
        return ["- none"]
    lines: list[str] = []
    for row in rows:
        detail = f" - {row['description']}" if row["description"] else ""
        acceptance = f" acceptance={row['acceptance']}" if row["acceptance"] else ""
        lines.append(f"- {row['item_id']}: {row['title']}{detail}{acceptance}")
    return lines


def topic_tasks_section_lines(db: sqlite3.Connection, topic_id: str) -> list[str]:
    sections = [
        ("Doing", "doing"),
        ("Todo", "todo"),
        ("Blocked", "blocked"),
        ("Done", "done"),
        ("Dropped", "dropped"),
    ]
    lines: list[str] = []
    for title, status in sections:
        lines += [f"### {title}", *topic_task_lines(db, topic_id, status), ""]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def render_topic_plan(db: sqlite3.Connection, topic_id: str) -> str:
    topic = get_topic(db, topic_id)
    plan = get_topic_plan(db, topic_id)
    lines = [
        "# Topic Plan",
        "",
        f"## {topic['title']}",
        "",
        f"- topic_id: {topic_id}",
        f"- status: {plan['status']}",
        f"- updated_at: {plan['updated_at']}",
        "",
        "## Goal",
        "",
        plan["goal"] or "none",
        "",
        "## Non Goals",
        *markdown_list(plan["non_goals_json"]),
        "",
        "## Acceptance",
        *markdown_list(plan["acceptance_json"]),
        "",
        "## Stop Conditions",
        *markdown_list(plan["stop_conditions_json"]),
        "",
        "## Escalation Conditions",
        *markdown_list(plan["escalation_conditions_json"]),
        "",
        "## Project Links",
        *project_topic_link_lines(db, topic_id=topic_id),
        "",
        "## Todo",
        *topic_task_lines(db, topic_id, "todo"),
        "",
        "## Doing",
        *topic_task_lines(db, topic_id, "doing"),
        "",
        "## Done",
        *topic_task_lines(db, topic_id, "done"),
        "",
        "## Blocked",
        *topic_task_lines(db, topic_id, "blocked"),
        "",
        "## Dropped",
        *topic_task_lines(db, topic_id, "dropped"),
        "",
    ]
    return "\n".join(lines)


def topic_board_task_lines(db: sqlite3.Connection, status: str, limit: int = 12) -> list[str]:
    rows = db.execute(
        """
        select topics.topic_id, topics.title as topic_title, topics.status as topic_status,
               topic_plan_items.item_id, topic_plan_items.title as item_title,
               topic_plan_items.description, topic_plan_items.acceptance
        from topic_plan_items
        join topics on topics.topic_id = topic_plan_items.topic_id
        where topic_plan_items.status = ?
        order by topic_plan_items.updated_at desc, topic_plan_items.created_at desc
        limit ?
        """,
        (status, limit),
    ).fetchall()
    if not rows:
        return ["- none"]
    lines: list[str] = []
    for row in rows:
        description = f" - {row['description']}" if row["description"] else ""
        acceptance = f" acceptance={row['acceptance']}" if row["acceptance"] else ""
        lines.append(
            f"- {row['topic_id']} {row['item_id']} {status}: {row['item_title']}{description}{acceptance} "
            f"topic_title={row['topic_title']} topic_status={row['topic_status']}"
        )
    return lines


def ready_to_satisfy_topic_lines(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        """
        select topics.*
        from topics
        join topic_plans on topic_plans.topic_id = topics.topic_id
        where topics.status in ('active', 'archived_open')
          and not exists (
              select 1
              from topic_plan_items
              where topic_plan_items.topic_id = topics.topic_id
                and topic_plan_items.status in ('todo', 'doing', 'blocked')
          )
        order by topics.updated_at desc, topics.created_at desc
        limit 8
        """
    ).fetchall()
    if not rows:
        return ["- none"]
    return [topic_brief_line(row) for row in rows]


def render_topic_board(db: sqlite3.Connection) -> str:
    current = active_topic(db)
    open_topics = db.execute(
        """
        select * from topics
        where status in ('active', 'archived_open')
        order by updated_at desc, created_at desc
        limit 12
        """
    ).fetchall()
    lines = [
        "# Project Topic Board",
        "",
        "## Default Topic",
    ]
    if current:
        lines.append(topic_brief_line(current))
    else:
        lines.append("- none")
    lines += [
        "",
        "## Open Topics",
    ]
    if open_topics:
        lines += [topic_brief_line(row) for row in open_topics]
    else:
        lines.append("- none")
    lines += [
        "",
        "## Project Links",
        *project_topic_link_lines(db),
        "",
        "## Doing Tasks",
        *topic_board_task_lines(db, "doing"),
        "",
        "## Blocked Tasks",
        *topic_board_task_lines(db, "blocked"),
        "",
        "## Recent Done Tasks",
        *topic_board_task_lines(db, "done"),
        "",
        "## Ready To Satisfy",
        *ready_to_satisfy_topic_lines(db),
        "",
    ]
    return "\n".join(lines)


def write_topic_board_projection(db: sqlite3.Connection) -> None:
    topics_dir().mkdir(parents=True, exist_ok=True)
    topic_board_path().write_text(render_topic_board(db), encoding="utf-8")


def write_topic_plan_projections(db: sqlite3.Connection) -> None:
    topics_dir().mkdir(parents=True, exist_ok=True)
    rows = db.execute("select topic_id from topic_plans order by updated_at desc").fetchall()
    for row in rows:
        path = topic_plan_path(row["topic_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_topic_plan(db, row["topic_id"]), encoding="utf-8")
    default_topic = active_topic(db)
    default_path = default_topic_plan_path()
    if default_topic:
        plan = db.execute("select 1 from topic_plans where topic_id = ?", (default_topic["topic_id"],)).fetchone()
        if plan:
            default_path.write_text(render_topic_plan(db, default_topic["topic_id"]), encoding="utf-8")
        elif default_path.exists():
            default_path.unlink()
    elif default_path.exists():
        default_path.unlink()
    write_topic_board_projection(db)
    write_project_topic_links_projection(db)


def render_topic_projection(db: sqlite3.Connection, topic: sqlite3.Row, active_projection: bool = False) -> str:
    title = "Active Topic" if active_projection else topic["title"]
    lines = [
        f"# {title}",
        "",
        f"## {topic['title']}",
        "",
        f"- topic_id: {topic['topic_id']}",
        f"- status: {topic['status']}",
        f"- summary: {topic['summary'] or 'none'}",
        f"- current_goal: {topic['current_goal'] or 'none'}",
        f"- restore_hint: {topic['restore_hint'] or 'none'}",
        f"- updated_at: {topic['updated_at']}",
        "",
        "## Recent Events",
        *topic_event_lines(db, topic["topic_id"]),
        "",
        "## Evidence Links",
        *topic_evidence_lines(db, topic["topic_id"]),
        "",
    ]
    return "\n".join(lines)


def render_no_active_topic() -> str:
    return "\n".join(
        [
            "# Active Topic",
            "",
            "## None",
            "",
            "- status: none",
            "- restore_hint: start a new topic or switch to an archived topic.",
            "",
        ]
    )


def write_topic_projections(db: sqlite3.Connection) -> None:
    topics_dir().mkdir(parents=True, exist_ok=True)
    topic_archive_dir().mkdir(parents=True, exist_ok=True)
    rows = db.execute("select * from topics order by updated_at desc, created_at desc").fetchall()
    active = [row for row in rows if row["status"] == "active"]
    if active:
        active_topic_path().write_text(render_topic_projection(db, active[0], active_projection=True), encoding="utf-8")
    else:
        active_topic_path().write_text(render_no_active_topic(), encoding="utf-8")
    index_lines = ["# Topic Index", ""]
    if not rows:
        index_lines += ["## No Topics", "", "- none", ""]
    for row in rows:
        index_lines += [
            f"## {row['title']}",
            "",
            f"- topic_id: {row['topic_id']}",
            f"- status: {row['status']}",
            f"- summary: {row['summary'] or 'none'}",
            f"- restore_hint: {row['restore_hint'] or 'none'}",
            "",
        ]
        archive_path = topic_archive_path(row["topic_id"])
        if row["status"] == "active":
            if archive_path.exists():
                archive_path.unlink()
        else:
            archive_path.write_text(render_topic_projection(db, row), encoding="utf-8")
    topic_index_path().write_text("\n".join(index_lines), encoding="utf-8")
    write_topic_plan_projections(db)


def topics_missing_plans(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        """
        select topics.*
        from topics
        left join topic_plans on topic_plans.topic_id = topics.topic_id
        where topic_plans.topic_id is null
        order by topics.updated_at desc, topics.created_at desc
        """
    ).fetchall()


def create_missing_topic_plans(db: sqlite3.Connection) -> int:
    missing = topics_missing_plans(db)
    timestamp = now_iso()
    for topic in missing:
        db.execute(
            """
            insert into topic_plans (
                topic_id, status, goal, non_goals_json, acceptance_json,
                stop_conditions_json, escalation_conditions_json, updated_at
            )
            values (?, 'open', '', '[]', '[]', '[]', '[]', ?)
            """,
            (topic["topic_id"], timestamp),
        )
    if missing:
        write_topic_projections(db)
    return len(missing)


def topic_plan_migration_warnings(db: sqlite3.Connection) -> list[str]:
    warnings = []
    for topic in topics_missing_plans(db):
        warnings.append(
            f"WARNING: topic {topic['topic_id']} has no topic plan; run `auto-iter migrate` to create an empty plan"
        )
    return warnings


def archive_current_topic(db: sqlite3.Connection, summary: str) -> sqlite3.Row | None:
    current = active_topic(db)
    if not current:
        return None
    if not summary:
        raise UserError("--current-summary is required when an active topic exists")
    updated_at = now_iso()
    restore_hint = f"Use `auto-iter topic switch --topic-id {current['topic_id']} --current-summary <summary>` to continue this topic."
    db.execute(
        """
        update topics
        set status = 'archived_open', summary = ?, restore_hint = ?, updated_at = ?
        where topic_id = ?
        """,
        (summary, restore_hint, updated_at, current["topic_id"]),
    )
    add_topic_event(db, current["topic_id"], "archive_open", summary)
    return current


def ensure_single_active_topic(db: sqlite3.Connection) -> None:
    active_count = db.execute("select count(*) from topics where status = 'active'").fetchone()[0]
    if active_count > 1:
        raise UserError("topic invariant violated: more than one active topic")


def command_topic_start(args: argparse.Namespace) -> int:
    with database() as db:
        archive_current_topic(db, args.current_summary or "")
        topic_id = new_id("T")
        timestamp = now_iso()
        restore_hint = f"Current active topic. Use `auto-iter topic satisfy --summary <summary>` when this stage is satisfied."
        db.execute(
            """
            insert into topics (topic_id, title, status, summary, current_goal, restore_hint, created_at, updated_at)
            values (?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (topic_id, args.title, args.summary or "", args.current_goal or "", restore_hint, timestamp, timestamp),
        )
        add_topic_event(db, topic_id, "create", args.summary or "")
        add_topic_event(db, topic_id, "switch_in", "new topic activated")
        ensure_single_active_topic(db)
        write_topic_projections(db)
    print(f"started topic {topic_id}")
    return 0


def command_topic_switch(args: argparse.Namespace) -> int:
    with database() as db:
        target = get_topic(db, args.topic_id)
        current = active_topic(db)
        if current and current["topic_id"] == target["topic_id"]:
            write_topic_projections(db)
            print(f"topic already active {target['topic_id']}")
            return 0
        archive_current_topic(db, args.current_summary or "")
        previous_status = target["status"]
        timestamp = now_iso()
        restore_hint = f"Current active topic. Use `auto-iter topic satisfy --summary <summary>` when this stage is satisfied."
        db.execute(
            "update topics set status = 'active', restore_hint = ?, updated_at = ? where topic_id = ?",
            (restore_hint, timestamp, target["topic_id"]),
        )
        if previous_status == "archived_satisfied":
            add_topic_event(db, target["topic_id"], "reopen", "reopened from archived_satisfied")
        add_topic_event(db, target["topic_id"], "switch_in", "topic activated")
        ensure_single_active_topic(db)
        write_topic_projections(db)
    print(f"switched topic {args.topic_id}")
    return 0


def command_topic_satisfy(args: argparse.Namespace) -> int:
    with database() as db:
        current = active_topic(db)
        if not current:
            raise UserError("no active topic")
        timestamp = now_iso()
        restore_hint = f"Use `auto-iter topic switch --topic-id {current['topic_id']} --current-summary <summary>` to reopen this satisfied topic."
        db.execute(
            """
            update topics
            set status = 'archived_satisfied', summary = ?, restore_hint = ?, updated_at = ?
            where topic_id = ?
            """,
            (args.summary, restore_hint, timestamp, current["topic_id"]),
        )
        add_topic_event(db, current["topic_id"], "archive_satisfied", args.summary)
        write_topic_projections(db)
    print(f"satisfied topic {current['topic_id']}")
    return 0


def command_topic_current(_args: argparse.Namespace) -> int:
    with database() as db:
        current = active_topic(db)
        if not current:
            write_topic_projections(db)
            raise UserError("no active topic")
        print(render_topic_projection(db, current, active_projection=True))
    return 0


def command_topic_list(_args: argparse.Namespace) -> int:
    with database() as db:
        rows = db.execute("select * from topics order by updated_at desc, created_at desc").fetchall()
    if not rows:
        print("no topics")
        return 0
    for row in rows:
        print(f"{row['topic_id']} {row['status']} title={row['title']} updated={row['updated_at']}")
        if row["summary"]:
            print(f"  summary: {row['summary']}")
        if row["restore_hint"]:
            print(f"  restore_hint: {row['restore_hint']}")
    return 0


def command_topic_show(args: argparse.Namespace) -> int:
    with database() as db:
        topic = get_topic(db, args.topic_id)
        print(render_topic_projection(db, topic, active_projection=topic["status"] == "active"))
    return 0


def validate_topic_evidence_id(db: sqlite3.Connection, evidence_type: str, evidence_id: str) -> None:
    if evidence_type not in TOPIC_EVIDENCE_TYPES:
        raise UserError(f"invalid topic evidence type: {evidence_type}")
    table_and_column = {
        "run": ("runs", "run_id"),
        "decision": ("decisions", "decision_id"),
        "artifact": ("artifacts", "artifact_id"),
    }[evidence_type]
    table, column = table_and_column
    row = db.execute(f"select 1 from {table} where {column} = ?", (evidence_id,)).fetchone()
    if not row:
        raise UserError(f"unknown {evidence_type} evidence_id: {evidence_id}")


def command_topic_link(args: argparse.Namespace) -> int:
    evidence_items = [("run", item) for item in args.run_id]
    evidence_items += [("decision", item) for item in args.decision_id]
    evidence_items += [("artifact", item) for item in args.artifact_id]
    if not evidence_items:
        raise UserError("at least one --run-id, --decision-id, or --artifact-id is required")
    with database() as db:
        resolution = resolve_write_topic_id(db, args.topic_id, args.allow_default_topic)
        timestamp = now_iso()
        for evidence_type, evidence_id in evidence_items:
            validate_topic_evidence_id(db, evidence_type, evidence_id)
            db.execute(
                """
                insert into topic_evidence_links (topic_id, evidence_type, evidence_id, summary, created_at)
                values (?, ?, ?, ?, ?)
                on conflict(topic_id, evidence_type, evidence_id)
                do update set summary = excluded.summary, created_at = excluded.created_at
                """,
                (resolution.topic_id, evidence_type, evidence_id, args.summary or "", timestamp),
            )
        add_topic_event(db, resolution.topic_id, "evidence_link", args.summary or "")
        write_topic_projections(db)
    print(f"resolved_topic_id: {resolution.topic_id}")
    print(f"resolved_topic_source: {resolution.source}")
    print(f"linked topic evidence {resolution.topic_id} count={len(evidence_items)}")
    return 0


def command_topic_evidence(args: argparse.Namespace) -> int:
    with database() as db:
        topic = get_topic(db, args.topic_id)
        print(f"# Topic Evidence Links")
        print()
        print(f"- topic_id: {topic['topic_id']}")
        print(f"- title: {topic['title']}")
        print()
        for line in topic_evidence_lines(db, args.topic_id, limit=args.latest):
            print(line)
    return 0


def command_topic_plan_set(args: argparse.Namespace) -> int:
    with database() as db:
        resolution = resolve_write_topic_id(db, args.topic_id, args.allow_default_topic)
        timestamp = now_iso()
        db.execute(
            """
            insert into topic_plans (
                topic_id, status, goal, non_goals_json, acceptance_json,
                stop_conditions_json, escalation_conditions_json, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(topic_id) do update set
                status = excluded.status,
                goal = excluded.goal,
                non_goals_json = excluded.non_goals_json,
                acceptance_json = excluded.acceptance_json,
                stop_conditions_json = excluded.stop_conditions_json,
                escalation_conditions_json = excluded.escalation_conditions_json,
                updated_at = excluded.updated_at
            """,
            (
                resolution.topic_id,
                args.status,
                args.goal or "",
                json.dumps(args.non_goal, ensure_ascii=False),
                json.dumps(args.acceptance, ensure_ascii=False),
                json.dumps(args.stop_condition, ensure_ascii=False),
                json.dumps(args.escalation_condition, ensure_ascii=False),
                timestamp,
            ),
        )
        write_topic_projections(db)
    print(f"resolved_topic_id: {resolution.topic_id}")
    print(f"resolved_topic_source: {resolution.source}")
    print(f"saved topic plan {resolution.topic_id}")
    return 0


def command_topic_plan_show(args: argparse.Namespace) -> int:
    with database() as db:
        print(render_topic_plan(db, args.topic_id))
    return 0


def command_topic_plan_current(_args: argparse.Namespace) -> int:
    with database() as db:
        current = active_topic(db)
        if not current:
            raise UserError("no default topic")
        print(render_topic_plan(db, current["topic_id"]))
    return 0


def command_topic_task_add(args: argparse.Namespace) -> int:
    with database() as db:
        resolution = resolve_write_topic_id(db, args.topic_id, args.allow_default_topic)
        timestamp = now_iso()
        item_id = new_id("I")
        db.execute(
            """
            insert into topic_plan_items (
                item_id, topic_id, status, title, description, acceptance,
                evidence_json, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                resolution.topic_id,
                args.status,
                args.title,
                args.description or "",
                args.acceptance or "",
                json.dumps(args.evidence, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        write_topic_projections(db)
    print(f"resolved_topic_id: {resolution.topic_id}")
    print(f"resolved_topic_source: {resolution.source}")
    print(f"added topic task {item_id}")
    return 0


def command_topic_task_set(args: argparse.Namespace) -> int:
    with database() as db:
        row = db.execute("select * from topic_plan_items where item_id = ?", (args.item_id,)).fetchone()
        if not row:
            raise UserError(f"unknown topic task item_id: {args.item_id}")
        evidence = json.loads(row["evidence_json"])
        evidence.extend(args.evidence)
        db.execute(
            """
            update topic_plan_items
            set status = ?, evidence_json = ?, updated_at = ?
            where item_id = ?
            """,
            (args.status, json.dumps(evidence, ensure_ascii=False), now_iso(), args.item_id),
        )
        write_topic_projections(db)
    print(f"updated topic task {args.item_id}")
    return 0


def command_topic_task_list(args: argparse.Namespace) -> int:
    with database() as db:
        get_topic(db, args.topic_id)
        rows = db.execute(
            """
            select item_id, status, title, description, acceptance
            from topic_plan_items
            where topic_id = ?
            order by updated_at desc, created_at desc
            """,
            (args.topic_id,),
        ).fetchall()
    if not rows:
        print("no topic tasks")
        return 0
    for row in rows:
        print(f"{row['item_id']} {row['status']} title={row['title']}")
        if row["description"]:
            print(f"  description: {row['description']}")
        if row["acceptance"]:
            print(f"  acceptance: {row['acceptance']}")
    return 0


def command_project_link_topic(args: argparse.Namespace) -> int:
    if not project_heading_exists(args.project_heading):
        raise UserError(f"project heading not found in project_plan.md: {args.project_heading}")
    with database() as db:
        get_topic(db, args.topic_id)
        timestamp = now_iso()
        db.execute(
            """
            insert into project_topic_links (
                project_heading, topic_id, relation, summary, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?)
            on conflict(project_heading, topic_id, relation) do update set
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (args.project_heading, args.topic_id, args.relation, args.summary or "", timestamp, timestamp),
        )
        add_topic_event(
            db,
            args.topic_id,
            "project-link",
            f"{args.relation} project heading {args.project_heading}",
        )
        write_topic_projections(db)
    print(f"linked project topic {args.topic_id}")
    print(f"project_heading: {args.project_heading}")
    print(f"relation: {args.relation}")
    return 0


def command_project_topic_links(args: argparse.Namespace) -> int:
    with database() as db:
        lines = project_topic_link_lines(db, project_heading=args.project_heading)
    print("# Project Topic Links")
    print()
    print(f"## {args.project_heading}")
    for line in lines:
        print(line)
    return 0


def command_topic_project_links(args: argparse.Namespace) -> int:
    with database() as db:
        get_topic(db, args.topic_id)
        lines = project_topic_link_lines(db, topic_id=args.topic_id)
    print("# Topic Project Links")
    print()
    print(f"## {args.topic_id}")
    for line in lines:
        print(line)
    return 0


def command_topic_board(_args: argparse.Namespace) -> int:
    with database() as db:
        write_topic_projections(db)
        board_md = render_topic_board(db)
        topic_board_path().write_text(board_md, encoding="utf-8")
    print(board_md, end="")
    return 0


def verify_installation(command_path: Path, installed_skills: list[tuple[str, Path]]) -> None:
    python_path = python_executable()
    if not python_path:
        raise UserError("install check failed: dependency missing: python")
    if not command_path.exists():
        raise UserError(f"install check failed: command wrapper missing: {command_path}")
    if not is_windows_platform() and not os.access(command_path, os.X_OK):
        raise UserError(f"install check failed: command is not executable: {command_path}")
    for skill_name, skill_dir in installed_skills:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists() or not skill_md.read_text(encoding="utf-8").strip():
            raise UserError(f"install check failed: skill not ready: {skill_name}")
    print("install check: ok")
    print(f"dependency ready: python ({python_path})")
    print(f"command ready: {command_path.name} ({command_path})")
    path_entries = [Path(entry).expanduser() for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    if command_path.parent not in path_entries:
        print(f"path hint: {command_path.parent} is not on PATH; use {command_path} or add that directory to PATH")
    for skill_name, skill_dir in installed_skills:
        print(f"skill ready: {skill_name} ({skill_dir})")


def new_id(prefix: str) -> str:
    value = hashlib.sha256(f"{prefix}:{now_iso()}:{os.getpid()}:{root()}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{value}"


def command_run_start(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    with database() as db:
        run_id = create_run_record(db, config, args.dataset, args.command, args.seed, args.session)
    print(f"started run {run_id}")
    return 0


def create_run_record(
    db: sqlite3.Connection,
    config: Any,
    dataset: str,
    command: str,
    seed: str | None = None,
    session: str | None = None,
) -> str:
    run_id = new_id("R")
    current_run_dir = run_dir(run_id)
    logs_dir(run_id).mkdir(parents=True, exist_ok=True)
    (current_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    for log_name in ["stdout.log", "stderr.log", "debug.jsonl"]:
        (logs_dir(run_id) / log_name).touch()
    config_text = json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True)
    (current_run_dir / "config_resolved.json").write_text(config_text + "\n", encoding="utf-8")
    config_hash = hash_data(config)
    project = db.execute("select project_id from projects limit 1").fetchone()
    project_id = project["project_id"] if project else "default"
    db.execute(
        """
        insert into runs (
            run_id, project_id, session_id, git_commit, git_branch, dataset_id,
            seed, command, config_json, config_hash, status, started_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)
        """,
        (
            run_id,
            project_id,
            session,
            git_commit(),
            git_branch(),
            dataset,
            seed,
            command,
            stable_json(config),
            config_hash,
            now_iso(),
        ),
    )
    return run_id


def normalize_metric(value: Any) -> tuple[float, str, str]:
    if isinstance(value, dict):
        metric_value = float(value["value"])
        unit = str(value.get("unit", ""))
        direction = str(value.get("direction", ""))
        return metric_value, unit, direction
    return float(value), "", ""


def add_artifact(db: sqlite3.Connection, run_id: str, artifact_path: str, kind: str = "other") -> None:
    path = Path(artifact_path).expanduser().resolve()
    if not path.exists():
        raise UserError(f"artifact does not exist: {path}")
    artifact_id = "A-" + hashlib.sha256(f"{run_id}:{path}".encode("utf-8")).hexdigest()[:10]
    db.execute(
        """
        insert or replace into artifacts (artifact_id, run_id, kind, path, sha256, summary)
        values (?, ?, ?, ?, ?, ?)
        """,
        (artifact_id, run_id, kind, str(path), file_sha256(path), path.name),
    )


def summarize_text(text: str, max_lines: int = 40, max_chars: int = 4000) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = ["... truncated earlier lines ...", *lines[-max_lines:]]
    summarized = "\n".join(lines)
    if len(summarized) > max_chars:
        summarized = "... truncated earlier characters ...\n" + summarized[-max_chars:]
    return summarized


def write_debug_event(run_id: str, event: str, payload: dict[str, Any]) -> None:
    path = logs_dir(run_id) / "debug.jsonl"
    record = {"time": now_iso(), "event": event, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_error_summary(run_id: str, returncode: int | None = None) -> None:
    stderr_path = logs_dir(run_id) / "stderr.log"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    lines = [
        "# Error Summary",
        "",
        f"- run_id: {run_id}",
        f"- returncode: {returncode if returncode is not None else 'unknown'}",
        "",
        "## stderr",
    ]
    if stderr_text.strip():
        lines += ["", "```text", summarize_text(stderr_text), "```"]
    else:
        lines.append("No stderr output.")
    (logs_dir(run_id) / "error_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_summary(db: sqlite3.Connection, run_id: str) -> None:
    run = db.execute("select * from runs where run_id = ?", (run_id,)).fetchone()
    if not run:
        raise UserError(f"unknown run_id: {run_id}")
    metrics = db.execute("select * from metrics where run_id = ? order by metric_name", (run_id,)).fetchall()
    artifacts = db.execute("select * from artifacts where run_id = ? order by path", (run_id,)).fetchall()
    lines = [
        "# Run Summary",
        "",
        f"- run_id: {run['run_id']}",
        f"- status: {run['status']}",
        f"- dataset_id: {run['dataset_id']}",
        f"- git_commit: {run['git_commit']}",
        f"- git_branch: {run['git_branch']}",
        f"- config_hash: {run['config_hash']}",
        f"- command: {run['command']}",
        "",
        "## Metrics",
    ]
    if metrics:
        for row in metrics:
            unit = f" {row['unit']}" if row["unit"] else ""
            direction = f" direction={row['direction']}" if row["direction"] else ""
            lines.append(f"- {row['metric_name']}: {row['metric_value']}{unit}{direction}")
    else:
        lines.append("- none")
    lines += ["", "## Artifacts"]
    if artifacts:
        for row in artifacts:
            lines.append(f"- {row['kind']}: {row['path']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Logs",
        f"- stdout: {logs_dir(run_id) / 'stdout.log'}",
        f"- stderr: {logs_dir(run_id) / 'stderr.log'}",
        f"- debug: {logs_dir(run_id) / 'debug.jsonl'}",
        f"- error_summary: {logs_dir(run_id) / 'error_summary.md'}",
        "",
    ]
    (run_dir(run_id) / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def finish_run_record(
    db: sqlite3.Connection,
    run_id: str,
    status: str,
    metrics: dict[str, Any],
    artifact_paths: list[str],
    returncode: int | None = None,
) -> None:
    if status not in RUN_STATUSES:
        raise UserError(f"invalid status: {status}")
    existing = db.execute("select run_id from runs where run_id = ?", (run_id,)).fetchone()
    if not existing:
        raise UserError(f"unknown run_id: {run_id}")
    for name, raw_value in metrics.items():
        value, unit, direction = normalize_metric(raw_value)
        db.execute(
            """
            insert or replace into metrics (run_id, metric_name, metric_value, unit, direction)
            values (?, ?, ?, ?, ?)
            """,
            (run_id, name, value, unit, direction),
        )
    for path in artifact_paths:
        add_artifact(db, run_id, path)
    summary = f"status={status}; metrics={', '.join(sorted(metrics))}"
    db.execute(
        "update runs set status = ?, ended_at = ?, summary = ? where run_id = ?",
        (status, now_iso(), summary, run_id),
    )
    write_error_summary(run_id, returncode)
    write_run_summary(db, run_id)


def command_run_finish(args: argparse.Namespace) -> int:
    metrics = read_json(args.metrics) if args.metrics else {}
    with database() as db:
        finish_run_record(db, args.run_id, args.status, metrics, args.artifact)
    print(f"finished run {args.run_id}")
    return 0


def command_run_exec(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    with database() as db:
        run_id = create_run_record(db, config, args.dataset, args.command, args.seed, args.session)
        write_debug_event(run_id, "started", {"command": args.command})
        result = subprocess.run(args.command, cwd=root(), text=True, capture_output=True, shell=True)
        (logs_dir(run_id) / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (logs_dir(run_id) / "stderr.log").write_text(result.stderr, encoding="utf-8")
        status = "success" if result.returncode == 0 else "failed"
        write_debug_event(
            run_id,
            "finished",
            {"returncode": result.returncode, "status": status},
        )
        metrics = read_json(args.metrics) if args.metrics and Path(args.metrics).exists() else {}
        finish_run_record(db, run_id, status, metrics, args.artifact, result.returncode)
    print(f"executed run {run_id} status={status} returncode={result.returncode}")
    return result.returncode


def command_run_list(args: argparse.Namespace) -> int:
    with database() as db:
        rows = db.execute(
            """
            select run_id, status, dataset_id, started_at, ended_at
            from runs
            order by started_at desc
            limit ?
            """,
            (args.latest,),
        ).fetchall()
    for row in rows:
        print(f"{row['run_id']} {row['status']} dataset={row['dataset_id']} started={row['started_at']}")
    return 0


def command_run_show(args: argparse.Namespace) -> int:
    with database() as db:
        run = db.execute("select * from runs where run_id = ?", (args.run_id,)).fetchone()
        if not run:
            raise UserError(f"unknown run_id: {args.run_id}")
        metrics = db.execute("select * from metrics where run_id = ? order by metric_name", (args.run_id,)).fetchall()
        artifacts = db.execute("select * from artifacts where run_id = ? order by path", (args.run_id,)).fetchall()
    data = dict(run)
    data["config_json"] = json.loads(data["config_json"])
    data["metrics"] = [dict(row) for row in metrics]
    data["artifacts"] = [dict(row) for row in artifacts]
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_route_param(spec: str) -> dict[str, Any]:
    parts = spec.split(":")
    if len(parts) != 3:
        raise UserError(f"invalid --route-param {spec!r}; expected name:min:max")
    name, minimum, maximum = parts
    if not name:
        raise UserError(f"invalid --route-param {spec!r}; name is empty")
    try:
        min_value = float(minimum)
        max_value = float(maximum)
    except ValueError as exc:
        raise UserError(f"invalid --route-param {spec!r}; min and max must be numbers") from exc
    if min_value > max_value:
        raise UserError(f"invalid --route-param {spec!r}; min must be <= max")
    return {"name": name, "min": min_value, "max": max_value}


def encode_route_rule(route_keywords: list[str], route_relation: str, route_params: list[str]) -> str:
    params = [parse_route_param(spec) for spec in route_params]
    return json.dumps(
        {
            "keywords": route_keywords,
            "relation": route_relation,
            "params": params,
        },
        ensure_ascii=False,
    )


def decode_route_rule(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if isinstance(data, list):
        return {"keywords": data, "relation": "keyword", "params": []}
    if not isinstance(data, dict):
        return {"keywords": [], "relation": "keyword", "params": []}
    return {
        "keywords": list(data.get("keywords") or []),
        "relation": str(data.get("relation") or "keyword"),
        "params": list(data.get("params") or []),
    }


def route_param_text(params: list[dict[str, Any]]) -> str:
    return ", ".join(f"{item['name']}:{item['min']:g}:{item['max']:g}" for item in params)


def config_value(config: Any, dotted_name: str) -> Any:
    current = config
    for part in dotted_name.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def route_rule_matches(rule: dict[str, Any], summary: str, config: Any) -> bool:
    haystack = summary + "\n" + stable_json(config)
    keywords = rule["keywords"]
    keywords_match = all(keyword in haystack for keyword in keywords)
    relation = rule["relation"]
    params = rule["params"]
    if relation == "parameter-space":
        if not params:
            return False
        for item in params:
            value = config_value(config, str(item["name"]))
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return False
            if numeric < float(item["min"]) or numeric > float(item["max"]):
                return False
        return keywords_match if keywords else True
    return bool(keywords) and keywords_match


def normalize_rule_evidence(spec: str) -> dict[str, str]:
    if ":" in spec:
        kind, value = spec.split(":", 1)
        kind = kind.strip().lower()
        value = value.strip()
        if not kind or not value:
            raise UserError(f"invalid --evidence {spec!r}; expected kind:value")
        return {"kind": kind, "value": value}
    if re.fullmatch(r"R-[A-Za-z0-9]+", spec):
        return {"kind": "run", "value": spec}
    if re.fullmatch(r"D-[A-Za-z0-9]+", spec):
        return {"kind": "decision", "value": spec}
    if re.fullmatch(r"T-[A-Za-z0-9]+", spec):
        return {"kind": "topic", "value": spec}
    if re.fullmatch(r"A-[0-9a-fA-F]{10,}", spec):
        return {"kind": "artifact", "value": spec}
    return {"kind": "text", "value": spec}


def encode_rule_evidence(items: list[str], notes: list[str]) -> str:
    return json.dumps(
        {
            "items": [normalize_rule_evidence(item) for item in items],
            "notes": [note for note in notes if note],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def decode_rule_evidence(raw: str) -> dict[str, Any]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        return {"items": [], "notes": []}
    items = data.get("items") or []
    notes = data.get("notes") or []
    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        value = str(item.get("value") or "").strip()
        if kind and value:
            normalized_items.append({"kind": kind, "value": value})
    return {"items": normalized_items, "notes": [str(note) for note in notes if str(note)]}


def validate_rule_evidence(db: sqlite3.Connection, evidence_json: str) -> None:
    payload = decode_rule_evidence(evidence_json)
    validators = {
        "run": ("runs", "run_id"),
        "decision": ("decisions", "decision_id"),
        "artifact": ("artifacts", "artifact_id"),
        "topic": ("topics", "topic_id"),
    }
    for item in payload["items"]:
        validator = validators.get(item["kind"])
        if not validator:
            continue
        table, column = validator
        row = db.execute(f"select 1 from {table} where {column} = ?", (item["value"],)).fetchone()
        if not row:
            raise UserError(f"unknown {item['kind']} evidence id: {item['value']}")


def rule_path(status: str, rule_id: str) -> Path:
    return rule_status_dir(status) / f"{rule_id}.md"


def rule_evidence_lines(payload: dict[str, Any]) -> list[str]:
    items = payload.get("items") or []
    notes = payload.get("notes") or []
    lines: list[str] = []
    if items:
        for item in items:
            lines.append(f"- {item['kind']}: {item['value']}")
    else:
        lines.append("- none")
    if notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.extend(f"- {note}" for note in notes)
    return lines


def write_rule_projection(row: sqlite3.Row) -> None:
    payload = decode_rule_evidence(row["evidence_json"])
    path = rule_path(row["status"], row["rule_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {row['title']}",
        "",
        f"- rule_id: {row['rule_id']}",
        f"- source_kind: {row['source_kind']}",
        f"- rule_kind: {row['rule_kind']}",
        f"- scope_kind: {row['scope_kind']}",
        f"- status: {row['status']}",
    ]
    if row["supersedes_rule_id"]:
        lines.append(f"- supersedes_rule_id: {row['supersedes_rule_id']}")
    lines += [
        f"- created_at: {row['created_at']}",
        f"- updated_at: {row['updated_at']}",
        "",
        "## Claim",
        "",
        row["claim"],
        "",
        "## Evidence",
        "",
        *rule_evidence_lines(payload),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def render_current_rules_snapshot(rows: list[sqlite3.Row]) -> str:
    lines = ["# Current Effective Rules", ""]
    if not rows:
        lines += ["- none", ""]
        return "\n".join(lines)
    for row in rows:
        lines += [
            f"## {row['title']}",
            "",
            f"- rule_id: {row['rule_id']}",
            f"- source_kind: {row['source_kind']}",
            f"- rule_kind: {row['rule_kind']}",
            f"- scope_kind: {row['scope_kind']}",
        ]
        if row["supersedes_rule_id"]:
            lines.append(f"- supersedes_rule_id: {row['supersedes_rule_id']}")
        lines += [
            "",
            row["claim"],
            "",
        ]
    return "\n".join(lines)


def write_rule_projections(db: sqlite3.Connection) -> None:
    rules_dir().mkdir(parents=True, exist_ok=True)
    for status in RULE_STATUSES:
        status_dir = rule_status_dir(status)
        status_dir.mkdir(parents=True, exist_ok=True)
        for path in status_dir.glob("*.md"):
            path.unlink()
    rows = db.execute("select * from rules order by updated_at desc, created_at desc").fetchall()
    for row in rows:
        write_rule_projection(row)
    active_rows = db.execute(
        "select * from rules where status = 'active' order by updated_at desc, created_at desc"
    ).fetchall()
    current_rules_snapshot_path().write_text(render_current_rules_snapshot(active_rows), encoding="utf-8")


def command_rule_add(args: argparse.Namespace) -> int:
    if args.source_kind not in RULE_SOURCE_KINDS:
        raise UserError(f"invalid rule source_kind: {args.source_kind}")
    if args.rule_kind not in RULE_KINDS:
        raise UserError(f"invalid rule rule_kind: {args.rule_kind}")
    if args.scope_kind not in RULE_SCOPE_KINDS:
        raise UserError(f"invalid rule scope_kind: {args.scope_kind}")
    if args.status not in RULE_STATUSES:
        raise UserError(f"invalid rule status: {args.status}")
    rule_id = new_id("RL")
    timestamp = now_iso()
    evidence_json = encode_rule_evidence(args.evidence or [], args.note or [])
    with database() as db:
        validate_rule_evidence(db, evidence_json)
        if args.supersedes_rule_id:
            old = db.execute("select * from rules where rule_id = ?", (args.supersedes_rule_id,)).fetchone()
            if not old:
                raise UserError(f"unknown supersedes_rule_id: {args.supersedes_rule_id}")
        db.execute(
            """
            insert into rules (
                rule_id, title, claim, source_kind, rule_kind, scope_kind, status,
                supersedes_rule_id, evidence_json, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule_id,
                args.title,
                args.claim,
                args.source_kind,
                args.rule_kind,
                args.scope_kind,
                args.status,
                args.supersedes_rule_id,
                evidence_json,
                timestamp,
                timestamp,
            ),
        )
        if args.supersedes_rule_id:
            db.execute(
                "update rules set status = 'superseded', updated_at = ? where rule_id = ?",
                (timestamp, args.supersedes_rule_id),
            )
        write_rule_projections(db)
    print(f"added rule {rule_id}")
    return 0


def command_rule_list(_args: argparse.Namespace) -> int:
    with database() as db:
        rows = db.execute(
            """
            select rule_id, title, source_kind, rule_kind, scope_kind, status, updated_at
            from rules
            order by updated_at desc, created_at desc
            """
        ).fetchall()
    for row in rows:
        print(
            f"{row['rule_id']} {row['title']} "
            f"source_kind={row['source_kind']} rule_kind={row['rule_kind']} "
            f"scope_kind={row['scope_kind']} status={row['status']} updated_at={row['updated_at']}"
        )
    return 0


def command_rule_show(args: argparse.Namespace) -> int:
    with database() as db:
        row = db.execute("select * from rules where rule_id = ?", (args.rule_id,)).fetchone()
        if not row:
            raise UserError(f"unknown rule_id: {args.rule_id}")
    payload = decode_rule_evidence(row["evidence_json"])
    data = dict(row)
    data["evidence_json"] = payload
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def decision_path(status: str, decision_id: str) -> Path:
    return state_path("decisions", status, f"{decision_id}.md")


def write_decision_projection(
    decision_id: str,
    status: str,
    title: str,
    claim: str,
    evidence: list[str],
    route_rule: dict[str, Any],
    reopen_condition: str,
    supersedes: str | None,
) -> None:
    path = decision_path(status, decision_id)
    lines = [
        f"# {title}",
        "",
        f"- decision_id: {decision_id}",
        f"- status: {status}",
        f"- evidence_run_ids: {', '.join(evidence)}",
    ]
    if supersedes:
        lines.append(f"- supersedes_decision_id: {supersedes}")
    if route_rule["relation"]:
        lines.append(f"- route_relation: {route_rule['relation']}")
    if route_rule["keywords"]:
        lines.append(f"- route_keywords: {', '.join(route_rule['keywords'])}")
    if route_rule["params"]:
        lines.append(f"- route_params: {route_param_text(route_rule['params'])}")
    if reopen_condition:
        lines.append(f"- reopen_condition: {reopen_condition}")
    lines += ["", "## 结论", claim, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def command_decision_add(args: argparse.Namespace) -> int:
    if args.status not in DECISION_STATUSES:
        raise UserError(f"invalid decision status: {args.status}")
    evidence = args.evidence or []
    if not evidence:
        raise UserError("at least one --evidence run_id is required")
    decision_id = new_id("D")
    route_keywords = args.route_keyword or []
    route_rule_json = encode_route_rule(route_keywords, args.route_relation, args.route_param or [])
    route_rule = decode_route_rule(route_rule_json)
    with database() as db:
        for run_id in evidence:
            if not db.execute("select run_id from runs where run_id = ?", (run_id,)).fetchone():
                raise UserError(f"unknown evidence run_id: {run_id}")
        db.execute(
            """
            insert into decisions (
                decision_id, status, title, claim, evidence_run_ids_json,
                route_keywords_json, supersedes_decision_id, reopen_condition, created_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                args.status,
                args.title,
                args.claim,
                json.dumps(evidence, ensure_ascii=False),
                route_rule_json,
                args.supersedes,
                args.reopen_condition or "",
                now_iso(),
            ),
        )
    write_decision_projection(
        decision_id,
        args.status,
        args.title,
        args.claim,
        evidence,
        route_rule,
        args.reopen_condition or "",
        args.supersedes,
    )
    print(f"added decision {decision_id}")
    return 0


def command_decision_supersede(args: argparse.Namespace) -> int:
    with database() as db:
        old = db.execute("select * from decisions where decision_id = ?", (args.old_id,)).fetchone()
        new = db.execute("select * from decisions where decision_id = ?", (args.new_id,)).fetchone()
        if not old:
            raise UserError(f"unknown old decision: {args.old_id}")
        if not new:
            raise UserError(f"unknown new decision: {args.new_id}")
        db.execute(
            "update decisions set status = 'superseded', supersedes_decision_id = ? where decision_id = ?",
            (args.new_id, args.old_id),
        )
    old_path = decision_path(old["status"], args.old_id)
    new_path = decision_path("superseded", args.old_id)
    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
    print(f"superseded decision {args.old_id} by {args.new_id}")
    return 0


def command_route_check(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    config_hash = hash_data(config)
    summary = args.summary
    matched: list[sqlite3.Row] = []
    reasons: list[str] = []
    with database() as db:
        exact = db.execute(
            "select run_id, status from runs where config_hash = ? order by started_at desc limit 1",
            (config_hash,),
        ).fetchone()
        if exact:
            reasons.append(f"same config already recorded by run {exact['run_id']} status={exact['status']}")
        decisions = db.execute(
            """
            select * from decisions
            where status in ('rejected', 'superseded')
            order by created_at desc
            """
        ).fetchall()
        for decision in decisions:
            rule = decode_route_rule(decision["route_keywords_json"])
            if route_rule_matches(rule, summary, config):
                matched.append(decision)
        result = "block" if matched or exact else "allow"
        check_id = new_id("C")
        db.execute(
            """
            insert into route_checks (
                check_id, created_at, proposed_config_hash, proposed_summary, result, matched_decision_ids_json
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (check_id, now_iso(), config_hash, summary, result, json.dumps([row["decision_id"] for row in matched])),
        )
    if result == "allow":
        print("ALLOWED")
        print("No rejected or superseded route matched this proposal.")
        return 0
    print("BLOCKED")
    for reason in reasons:
        print(f"- {reason}")
    for decision in matched:
        rule = decode_route_rule(decision["route_keywords_json"])
        evidence = ", ".join(json.loads(decision["evidence_run_ids_json"]))
        print(f"- {decision['decision_id']}: {decision['title']}")
        print(f"  route_relation: {rule['relation']}")
        if rule["params"]:
            print(f"  route_params: {route_param_text(rule['params'])}")
        print(f"  evidence_run_ids: {evidence}")
        if decision["reopen_condition"]:
            print(f"  reopen_condition: {decision['reopen_condition']}")
    return 2


def latest_runs(db: sqlite3.Connection) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
    success = db.execute(
        "select * from runs where status = 'success' order by ended_at desc, rowid desc limit 1"
    ).fetchone()
    failed = db.execute(
        "select * from runs where status in ('failed', 'aborted') order by ended_at desc, rowid desc limit 1"
    ).fetchone()
    return success, failed


def artifact_lines(db: sqlite3.Connection, run_id: str) -> list[str]:
    rows = db.execute("select kind, path from artifacts where run_id = ? order by path", (run_id,)).fetchall()
    return [f"  - {row['kind']}: {row['path']}" for row in rows]


def current_baseline_lines(
    db: sqlite3.Connection,
    success: sqlite3.Row | None,
    active: list[sqlite3.Row],
    current_topic: sqlite3.Row | None,
) -> list[str]:
    primary_decision = active[0] if active else None
    if primary_decision:
        accepted_start = f"decision {primary_decision['decision_id']}: {primary_decision['title']}"
        why_current = primary_decision["claim"]
        evaluation_entry = str(decision_path(primary_decision["status"], primary_decision["decision_id"]).resolve())
        last_confirmed_at = primary_decision["created_at"]
    elif success:
        accepted_start = f"run {success['run_id']}: dataset={success['dataset_id']} status={success['status']}"
        why_current = current_topic["summary"] if current_topic and current_topic["summary"] else "not recorded"
        evaluation_entry = "not recorded"
        last_confirmed_at = success["ended_at"] or success["started_at"]
    else:
        accepted_start = "not recorded"
        why_current = current_topic["summary"] if current_topic and current_topic["summary"] else "not recorded"
        evaluation_entry = "not recorded"
        last_confirmed_at = "not recorded"

    if success:
        accepted_result = f"run {success['run_id']}: dataset={success['dataset_id']} status={success['status']}"
        provenance_entry = str((run_dir(success["run_id"]) / "config_resolved.json").resolve())
    else:
        accepted_result = "not recorded"
        provenance_entry = "not recorded"

    diagnostic_entry = "not recorded"
    if current_topic:
        topic_artifact = db.execute(
            """
            select artifacts.path
            from topic_evidence_links
            join artifacts on artifacts.artifact_id = topic_evidence_links.evidence_id
            where topic_evidence_links.topic_id = ?
              and topic_evidence_links.evidence_type = 'artifact'
            order by topic_evidence_links.created_at desc, topic_evidence_links.rowid desc
            limit 1
            """,
            (current_topic["topic_id"],),
        ).fetchone()
        if topic_artifact:
            diagnostic_entry = topic_artifact["path"]
    if diagnostic_entry == "not recorded" and success:
        run_artifact = db.execute(
            "select path from artifacts where run_id = ? order by path limit 1",
            (success["run_id"],),
        ).fetchone()
        if run_artifact:
            diagnostic_entry = run_artifact["path"]

    return [
        f"- accepted_start: {accepted_start}",
        f"- accepted_result: {accepted_result}",
        f"- why_current: {why_current}",
        f"- evaluation_entry: {evaluation_entry}",
        f"- provenance_entry: {provenance_entry}",
        f"- diagnostic_entry: {diagnostic_entry}",
        f"- last_confirmed_at: {last_confirmed_at}",
    ]


def topic_brief_line(row: sqlite3.Row) -> str:
    summary = f" summary={row['summary']}" if row["summary"] else ""
    return f"- {row['topic_id']} {row['status']} title={row['title']}{summary}"


def topic_summary_lines(db: sqlite3.Connection) -> list[str]:
    current = active_topic(db)
    recent = db.execute(
        "select * from topics order by updated_at desc, created_at desc limit 5"
    ).fetchall()
    open_topics = db.execute(
        """
        select * from topics
        where status in ('active', 'archived_open')
        order by updated_at desc, created_at desc
        limit 8
        """
    ).fetchall()
    blocked_tasks = db.execute(
        """
        select topics.topic_id, topics.title as topic_title,
               topic_plan_items.item_id, topic_plan_items.title as item_title
        from topic_plan_items
        join topics on topics.topic_id = topic_plan_items.topic_id
        where topic_plan_items.status = 'blocked'
        order by topic_plan_items.updated_at desc, topic_plan_items.created_at desc
        limit 8
        """
    ).fetchall()
    lines = ["### Default Topic"]
    if current:
        lines.append(topic_brief_line(current))
    else:
        lines.append("- none")
    lines += ["", "### Recently Updated Topics"]
    if recent:
        lines += [topic_brief_line(row) for row in recent]
    else:
        lines.append("- none")
    lines += ["", "### Open Topics"]
    if open_topics:
        lines += [topic_brief_line(row) for row in open_topics]
    else:
        lines.append("- none")
    lines += ["", "### Blocked Topic Tasks"]
    if blocked_tasks:
        for row in blocked_tasks:
            lines.append(
                f"- {row['topic_id']} {row['item_id']}: {row['item_title']} topic_title={row['topic_title']}"
            )
    else:
        lines.append("- none")
    return lines


def handoff_read_order_lines() -> list[str]:
    entries = []
    agents_path = root() / "AGENTS.md"
    if agents_path.exists():
        entries.append(str(agents_path))
    entries.append(str(state_path("handoffs", "latest_handoff.md")))
    project_plan = state_path("plans", "project_plan.md")
    project_record_rules = state_path("plans", "project_record_rules.md")
    project_links = project_topic_links_path()
    if project_plan.exists():
        entries.append(str(project_plan))
    if project_record_rules.exists():
        entries.append(str(project_record_rules))
    if project_links.exists():
        entries.append(str(project_links))
    entries += [
        str(state_path("plans", "global_plan.md")),
        str(state_path("plans", "version_iterations.md")),
        str(state_path("plans", "active_plan.md")),
        str(active_topic_path()),
        str(topic_board_path()),
        str(db_path()),
        f"{state_path('decisions')}（只信任 `auto-iter context index` 未标记为 orphan/stale 的 projection）。",
        "用 `auto-iter context index` 查看可按需读取的标题索引和 projection warnings。",
        "只有用户要求或确认切回 archived topic 时才读取 topics/archive/。",
        "只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。",
        "只有初次开始项目或明确缺失信息时才读取 raw_input/。",
    ]
    return [f"{index}. {entry}" for index, entry in enumerate(entries, start=1)]


def topic_handoff_read_order_lines(topic_id: str) -> list[str]:
    entries = []
    agents_path = root() / "AGENTS.md"
    if agents_path.exists():
        entries.append(str(agents_path))
    entries.append(str(topic_handoff_path(topic_id)))
    plan_path = topic_plan_path(topic_id)
    if plan_path.exists():
        entries.append(str(plan_path))
    project_plan = state_path("plans", "project_plan.md")
    project_record_rules = state_path("plans", "project_record_rules.md")
    if project_plan.exists():
        entries.append(str(project_plan))
    if project_record_rules.exists():
        entries.append(str(project_record_rules))
    entries += [
        str(topic_index_path()),
        str(active_topic_path()),
        str(state_path("plans", "active_plan.md")),
        str(state_path("plans", "version_iterations.md")),
        str(state_path("plans", "global_plan.md")),
        str(db_path()),
        f"用 `auto-iter topic evidence --topic-id {topic_id}` 查看该 topic 的 run、decision、artifact 证据链。",
        "用 `auto-iter context index` 查看可按需读取的标题索引和 projection warnings。",
        "只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。",
    ]
    return [f"{index}. {entry}" for index, entry in enumerate(entries, start=1)]


def build_handoff(db: sqlite3.Connection) -> tuple[str, str | None]:
    write_topic_projections(db)
    success, failed = latest_runs(db)
    active = db.execute("select * from decisions where status = 'active' order by created_at desc").fetchall()
    rejected = db.execute("select * from decisions where status = 'rejected' order by created_at desc").fetchall()
    open_items = db.execute("select * from decisions where status = 'open' order by created_at desc").fetchall()
    current_topic = active_topic(db)
    project = db.execute("select current_goal from projects limit 1").fetchone()
    current_goal = project["current_goal"] if project and project["current_goal"] else "未设置；请在下一轮实验前明确当前优化目标。"
    lines = [
        "# Latest Handoff",
        "",
        "## 当前目标",
        f"- {current_goal}",
        "",
        "## 当前快照",
        f"- root: {root()}",
        f"- branch: {git_branch()}",
        f"- commit: {git_commit()}",
        f"- latest_successful_run_id: {success['run_id'] if success else 'none'}",
        f"- latest_failed_run_id: {failed['run_id'] if failed else 'none'}",
    ]
    project_plan = state_path("plans", "project_plan.md")
    project_record_rules = state_path("plans", "project_record_rules.md")
    project_links = project_topic_links_path()
    if project_plan.exists():
        lines.append(f"- project_plan: {project_plan}")
    if project_record_rules.exists():
        lines.append(f"- project_record_rules: {project_record_rules}")
    if project_links.exists():
        lines.append(f"- project_topic_links: {project_links}")
    global_key = "global_plan_compat" if project_plan.exists() else "global_plan"
    lines += [
        f"- {global_key}: {state_path('plans', 'global_plan.md')}",
        f"- version_task_tracking: {state_path('plans', 'version_iterations.md')}",
        f"- active_plan: {state_path('plans', 'active_plan.md')}",
        f"- active_topic: {active_topic_path()}",
        f"- topic_index: {topic_index_path()}",
        f"- topic_board: {topic_board_path()}",
        "",
        "## 当前 Topic",
    ]
    if current_topic:
        lines += [
            f"- topic_id: {current_topic['topic_id']}",
            f"- title: {current_topic['title']}",
            f"- status: {current_topic['status']}",
            f"- summary: {current_topic['summary'] or 'none'}",
            f"- restore_hint: {current_topic['restore_hint'] or 'none'}",
        ]
    else:
        lines.append("- none")
    lines += [
        "",
        "## Topic Summary",
        *topic_summary_lines(db),
        "",
        "## Project Topic Links",
    ]
    if current_topic:
        lines += project_topic_link_lines(db, topic_id=current_topic["topic_id"])
    else:
        lines.append("- none")
    lines += [
        "",
        "## Current Baseline",
        *current_baseline_lines(db, success, active, current_topic),
        "",
        "## Topic Evidence Links",
    ]
    if current_topic:
        lines += topic_evidence_lines(db, current_topic["topic_id"], limit=8)
    else:
        lines.append("- none")
    lines += [
        "",
        "## 最近成功实验",
    ]
    if success:
        lines.append(f"- {success['run_id']}: dataset={success['dataset_id']} status={success['status']}")
        lines += artifact_lines(db, success["run_id"])
    else:
        lines.append("- none")
    lines += ["", "## 当前有效结论"]
    if active:
        for row in active:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            lines.append(f"  - {row['claim']}")
    else:
        lines.append("- none")
    lines += ["", "## 已废弃且不要重复的路线"]
    if rejected:
        for row in rejected:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            if row["reopen_condition"]:
                lines.append(f"  - reopen_condition: {row['reopen_condition']}")
    else:
        lines.append("- none")
    lines += ["", "## 未决假设"]
    if open_items:
        for row in open_items:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            lines.append(f"  - {row['claim']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## 下一步最小实验集合",
        "1. 先运行 `auto-iter route check --config <file> --summary <中文路线说明>`。",
        "2. 若允许，再用 `auto-iter run exec` 执行实验，或用 `auto-iter run start` 和 `auto-iter run finish` 分步写回指标和工件。",
        "3. 实验后用 `auto-iter decision add` 写入结论状态。",
        "4. 会话结束前运行 `auto-iter handoff generate` 和 `auto-iter handoff validate`。",
        "",
        "## 读取顺序",
        *handoff_read_order_lines(),
        "",
    ]
    return "\n".join(lines), success["run_id"] if success else None


def build_topic_handoff(db: sqlite3.Connection, topic_id: str) -> tuple[str, str | None]:
    write_topic_projections(db)
    topic = get_topic(db, topic_id)
    success, failed = latest_runs(db)
    active = db.execute("select * from decisions where status = 'active' order by created_at desc").fetchall()
    plan = db.execute("select * from topic_plans where topic_id = ?", (topic_id,)).fetchone()
    plan_path = topic_plan_path(topic_id)
    handoff_path = topic_handoff_path(topic_id)
    lines = [
        "# Topic Handoff",
        "",
        "## Topic Snapshot",
        f"- root: {root()}",
        f"- branch: {git_branch()}",
        f"- commit: {git_commit()}",
        f"- topic_handoff: {handoff_path}",
        f"- topic_id: {topic['topic_id']}",
        f"- title: {topic['title']}",
        f"- status: {topic['status']}",
        f"- summary: {topic['summary'] or 'none'}",
        f"- restore_hint: {topic['restore_hint'] or 'none'}",
        f"- topic_plan: {plan_path if plan_path.exists() else 'none'}",
        f"- latest_successful_run_id: {success['run_id'] if success else 'none'}",
        f"- latest_failed_run_id: {failed['run_id'] if failed else 'none'}",
        "",
        "## Topic Plan",
    ]
    if plan:
        lines += [
            f"- status: {plan['status']}",
            f"- updated_at: {plan['updated_at']}",
            "",
            "### Goal",
            plan["goal"] or "none",
            "",
            "### Acceptance",
            *markdown_list(plan["acceptance_json"]),
            "",
            "### Stop Conditions",
            *markdown_list(plan["stop_conditions_json"]),
            "",
            "### Escalation Conditions",
            *markdown_list(plan["escalation_conditions_json"]),
        ]
    else:
        lines.append("- none")
    lines += [
        "",
        "## Topic Tasks",
        *topic_tasks_section_lines(db, topic_id),
        "",
        "## Current Baseline",
        *current_baseline_lines(db, success, active, topic),
        "",
        "## Topic Evidence Links",
        *topic_evidence_lines(db, topic_id, limit=12),
        "",
        "## 下一步最小实验集合",
        f"1. 继续该 topic 前确认 `auto-iter doctor --topic-id {topic_id}` 输出的 resolved topic 正确。",
        "2. 实验前运行 `auto-iter route check --config <file> --summary <中文路线说明>`。",
        "3. 实验后用 `auto-iter topic link` 把 run、decision 或 artifact 关联到该 topic。",
        f"4. 会话结束前运行 `auto-iter handoff generate --topic-id {topic_id}` 和 `auto-iter handoff validate --topic-id {topic_id}`。",
        "",
        "## 读取顺序",
        *topic_handoff_read_order_lines(topic_id),
        "",
    ]
    return "\n".join(lines), success["run_id"] if success else None


def validate_handoff_text(text: str) -> list[str]:
    errors: list[str] = []
    required_sections = [
        "## 当前目标",
        "## 当前快照",
        "## 当前 Topic",
        "## Topic Summary",
        "## Current Baseline",
        "## Topic Evidence Links",
        "## 最近成功实验",
        "## 当前有效结论",
        "## 已废弃且不要重复的路线",
        "## 未决假设",
        "## 下一步最小实验集合",
        "## 读取顺序",
    ]
    for section in required_sections:
        if section not in text:
            errors.append(f"missing section: {section}")
    project_plan = state_path("plans", "project_plan.md")
    project_record_rules = state_path("plans", "project_record_rules.md")
    project_links = project_topic_links_path()
    global_key = "global_plan_compat" if project_plan.exists() else "global_plan"
    required_paths = {
        global_key: state_path("plans", "global_plan.md"),
        "version_task_tracking": state_path("plans", "version_iterations.md"),
        "active_plan": state_path("plans", "active_plan.md"),
        "active_topic": active_topic_path(),
        "topic_index": topic_index_path(),
        "topic_board": topic_board_path(),
    }
    if project_plan.exists():
        required_paths["project_plan"] = project_plan
    if project_record_rules.exists():
        required_paths["project_record_rules"] = project_record_rules
    if project_links.exists():
        required_paths["project_topic_links"] = project_links
    for key, path in required_paths.items():
        expected = f"- {key}: {path}"
        if expected not in text:
            errors.append(f"missing snapshot path: {key}")
        elif not path.exists():
            errors.append(f"snapshot path does not exist: {path}")
    if project_plan.exists() and str(project_plan) not in text:
        errors.append("read order missing project plan")
    if project_record_rules.exists() and str(project_record_rules) not in text:
        errors.append("read order missing project record rules")
    if project_links.exists() and str(project_links) not in text:
        errors.append("read order missing project topic links")
    if str(state_path("plans", "global_plan.md")) not in text:
        errors.append("read order missing global plan")
    return errors


def validate_topic_handoff_text(text: str, topic_id: str, path: Path) -> list[str]:
    errors: list[str] = []
    required_sections = [
        "# Topic Handoff",
        "## Topic Snapshot",
        "## Topic Plan",
        "## Topic Tasks",
        "## Current Baseline",
        "## Topic Evidence Links",
        "## 下一步最小实验集合",
        "## 读取顺序",
    ]
    for section in required_sections:
        if section not in text:
            errors.append(f"missing section: {section}")
    required_lines = {
        "topic_id": f"- topic_id: {topic_id}",
        "topic_handoff": f"- topic_handoff: {path}",
    }
    for key, expected in required_lines.items():
        if expected not in text:
            errors.append(f"missing topic handoff field: {key}")
    if not path.exists():
        errors.append(f"topic handoff path does not exist: {path}")
    return errors


def command_handoff_generate(args: argparse.Namespace) -> int:
    path, _based_on_run_id = save_handoff(args.topic_id)
    if args.print_path:
        print(f"generated {path.resolve()}")
    return 0


def save_handoff(topic_id: str | None = None) -> tuple[Path, str | None]:
    with database() as db:
        if topic_id:
            get_topic(db, topic_id)
            path = topic_handoff_path(topic_id)
            handoff_md, based_on_run_id = build_topic_handoff(db, topic_id)
            archive = topic_handoff_archive_dir(topic_id) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            path = state_path("handoffs", "latest_handoff.md")
            handoff_md, based_on_run_id = build_handoff(db)
            archive = state_path("handoffs", "archive", f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(handoff_md, encoding="utf-8")
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(handoff_md, encoding="utf-8")
        handoff_id = new_id("H")
        db.execute(
            """
            insert into handoffs (handoff_id, created_at, based_on_run_id, path, handoff_md)
            values (?, ?, ?, ?, ?)
            """,
            (handoff_id, now_iso(), based_on_run_id, str(path.resolve()), handoff_md),
        )
    return path, based_on_run_id


def command_handoff_validate(args: argparse.Namespace) -> int:
    path = topic_handoff_path(args.topic_id) if args.topic_id else state_path("handoffs", "latest_handoff.md")
    if not path.exists():
        print("INVALID")
        print(f"- handoff missing: {path.resolve()}")
        return 1
    if args.topic_id:
        with database() as db:
            get_topic(db, args.topic_id)
        errors = validate_topic_handoff_text(path.read_text(encoding="utf-8"), args.topic_id, path)
    else:
        errors = validate_handoff_text(path.read_text(encoding="utf-8"))
    _valid_decisions, projection_warnings = decision_projection_consistency()
    errors.extend(projection_warnings)
    migration_warnings: list[str] = []
    with database() as db:
        migration_warnings = topic_plan_migration_warnings(db)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID")
    print(f"validated {path.resolve()}")
    for warning in migration_warnings:
        print(warning)
    return 0


def command_checkpoint_save(args: argparse.Namespace) -> int:
    path, _based_on_run_id = save_handoff(args.topic_id)
    if args.topic_id:
        errors = validate_topic_handoff_text(path.read_text(encoding="utf-8"), args.topic_id, path)
    else:
        errors = validate_handoff_text(path.read_text(encoding="utf-8"))
    print("CHECKPOINT SAVED")
    print(f"text: {args.text}")
    print(f"handoff: {path.resolve()}")
    print(f"handoff_valid: {'no' if errors else 'yes'}")
    print("commit_push: not requested")
    print("- This is a mid-session record; continue the current Codex session unless the user says to end it.")
    print("- Use the same state-save scope as session end before or during this checkpoint.")
    print("- Do not commit or push unless the user explicitly asks.")
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    return 0


def command_resume(args: argparse.Namespace) -> int:
    path = topic_handoff_path(args.topic_id) if args.topic_id else state_path("handoffs", "latest_handoff.md")
    if not path.exists():
        print(f"handoff missing: {path.resolve()}")
        print("run `auto-iteration handoff generate` after at least one recorded run")
        return 1
    print(f"read first: {path.resolve()}")
    print(path.read_text(encoding="utf-8"))
    return 0


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def display_relative_path(path: Path) -> Path:
    return path.resolve().relative_to(root())


def state_relative_path(path: Path) -> Path:
    return path.resolve().relative_to(state_root())


@dataclass(frozen=True)
class SearchDocument:
    doc_id: str
    source_type: str
    source_id: str
    path: Path
    heading: str
    title: str
    body: str
    related_ids: list[str]


def decision_projection_files() -> list[Path]:
    return sorted(path.resolve() for path in state_path("decisions").glob("*/*.md") if path.is_file())


def decision_statuses_from_db() -> dict[str, str]:
    try:
        with database() as db:
            rows = db.execute("select decision_id, status from decisions").fetchall()
    except (sqlite3.Error, UserError):
        return {}
    return {row["decision_id"]: row["status"] for row in rows}


def decision_projection_consistency() -> tuple[list[Path], list[str]]:
    statuses = decision_statuses_from_db()
    valid: list[Path] = []
    warnings: list[str] = []
    for path in decision_projection_files():
        rel = display_relative_path(path)
        decision_id = path.stem
        projected_status = path.parent.name
        actual_status = statuses.get(decision_id)
        if actual_status is None:
            warnings.append(f"orphan decision projection skipped: {rel} (missing SQLite decision {decision_id})")
        elif actual_status != projected_status:
            warnings.append(
                f"stale decision projection skipped: {rel} "
                f"(SQLite status is {actual_status})"
            )
        else:
            valid.append(path)
    return valid, warnings


def context_files(include_raw_input: bool) -> list[Path]:
    patterns = [
        "plans/*.md",
        "handoffs/latest_handoff.md",
        "rules/current_effective.md",
        "rules/*/*.md",
        "topics/*.md",
        "topics/*/plan.md",
        "topics/*/latest_handoff.md",
        "topics/archive/*.md",
        "runs/*/summary.md",
        "runs/*/logs/error_summary.md",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(state_root().glob(pattern))
    valid_decisions, _warnings = decision_projection_consistency()
    files.extend(valid_decisions)
    if include_raw_input:
        files.extend(path for path in state_path("raw_input").glob("**/*") if path.is_file())
    return sorted({path.resolve() for path in files if path.is_file()})


def markdown_headings(path: Path) -> list[str]:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return []
    headings: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            marker, _, title = stripped.partition(" ")
            if marker and set(marker) == {"#"} and title:
                headings.append(stripped)
    return headings


def command_context_index(args: argparse.Namespace) -> int:
    print("# Context Index")
    for path in context_files(args.include_raw_input):
        rel = display_relative_path(path)
        print(f"- path: {rel}")
        headings = markdown_headings(path)
        if headings:
            for heading in headings:
                print(f"  - {heading}")
        else:
            print("  - no markdown headings")
    _valid_decisions, warnings = decision_projection_consistency()
    if warnings:
        print("# Projection Warnings")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def heading_level(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def heading_title(line: str) -> str:
    return line.lstrip("#").strip()


def extract_heading_section(path: Path, heading: str) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and heading_title(stripped) == heading:
            start = index
            level = heading_level(stripped)
            break
    if start is None:
        raise UserError(f"heading not found: {heading}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("#") and heading_level(stripped) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).rstrip() + "\n"


def command_context_show(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        raise UserError(f"context path does not exist: {path}")
    if is_under(path, state_path("raw_input")) and not args.allow_raw_input:
        raise UserError("raw_input requires --allow-raw-input")
    if not is_under(path, root()):
        raise UserError(f"context path must be under project root: {path}")
    print(extract_heading_section(path, args.heading), end="")
    return 0


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def search_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[\w./\\-]+", text.lower(), flags=re.UNICODE):
        ascii_parts = [part for part in re.split(r"[./\\\-_]+", raw) if len(part) >= 2 and not has_cjk(part)]
        for part in ascii_parts:
            tokens.append(part)
        if not has_cjk(raw):
            compact = re.sub(r"[^a-z0-9_]", "", raw)
            if len(compact) >= 2:
                tokens.append(compact)
            continue
        chars = [char for char in raw if "\u4e00" <= char <= "\u9fff"]
        for size in (2, 3):
            if len(chars) >= size:
                tokens.extend("".join(chars[index : index + size]) for index in range(len(chars) - size + 1))
        if len(chars) == 1:
            tokens.append(chars[0])
    return tokens


def markdown_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() not in {".md", ".markdown"}:
        return [("", text)]
    lines = text.splitlines()
    heading_rows: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        marker, _, title = stripped.partition(" ")
        if marker and set(marker) == {"#"} and title:
            heading_rows.append((index, len(marker), title.strip()))
    if not heading_rows:
        return [("", text)]
    sections: list[tuple[str, str]] = []
    for item_index, (start, level, title) in enumerate(heading_rows):
        end = len(lines)
        for next_start, next_level, _next_title in heading_rows[item_index + 1 :]:
            if next_level <= level:
                end = next_start
                break
        section = "\n".join(lines[start:end]).strip()
        if section:
            sections.append((title, section))
    return sections


def infer_source_type_and_id(path: Path, body: str) -> tuple[str, str]:
    rel = state_relative_path(path).as_posix()
    parts = rel.split("/")
    if parts[:1] == ["plans"]:
        return "plan", path.stem
    if rel == "handoffs/latest_handoff.md":
        return "handoff", "latest_handoff"
    if rel == "rules/current_effective.md":
        return "rule_snapshot", "current_effective"
    if parts[:1] == ["rules"] and len(parts) >= 3:
        return "rule", path.stem
    if parts[:1] == ["decisions"] and len(parts) >= 3:
        return "decision", path.stem
    if parts[:1] == ["runs"] and len(parts) >= 3:
        if parts[-1] == "summary.md":
            return "run", parts[1]
        if parts[-1] == "error_summary.md":
            return "error_summary", parts[1]
        return "run_artifact", parts[1]
    if parts[:1] == ["topics"]:
        if rel == "topics/board.md":
            return "topic_board", "board"
        if len(parts) >= 3 and parts[2] == "plan.md":
            return "topic_plan", parts[1]
        if len(parts) >= 3 and parts[2] == "latest_handoff.md":
            return "topic_handoff", parts[1]
        if len(parts) >= 3 and parts[1] == "archive":
            return "topic", path.stem
        match = re.search(r"topic_id:\s*(T-[A-Za-z0-9]+)", body)
        return "topic", match.group(1) if match else path.stem
    if parts[:1] == ["raw_input"]:
        return "raw_input", path.stem
    return "file", path.stem


def extract_related_ids(text: str) -> list[str]:
    ids = re.findall(r"\b(?:RL|R|D|T|H)-[A-Za-z0-9]+\b", text)
    ids.extend(re.findall(r"\bA-[0-9a-fA-F]{10,}\b", text))
    return sorted(set(ids))


def is_structured_search_id(value: str) -> bool:
    return bool(re.fullmatch(r"(?:RL|R|D|T|H)-[A-Za-z0-9]+|A-[0-9a-fA-F]{10,}", value))


def document_id(path: Path, heading: str, section_index: int) -> str:
    rel = state_relative_path(path).as_posix()
    digest = hashlib.sha256(f"{rel}\n{heading}\n{section_index}".encode("utf-8")).hexdigest()[:16]
    return f"S-{digest}"


def collect_search_documents(include_raw_input: bool) -> list[SearchDocument]:
    documents: list[SearchDocument] = []
    for path in context_files(include_raw_input):
        if not include_raw_input and is_under(path, state_path("raw_input")):
            continue
        for section_index, (heading, body) in enumerate(markdown_sections(path)):
            source_type, source_id = infer_source_type_and_id(path, body)
            title = heading or path.name
            related = extract_related_ids(body)
            if source_id and is_structured_search_id(source_id):
                related = sorted(set([source_id, *related]))
            documents.append(
                SearchDocument(
                    doc_id=document_id(path, heading, section_index),
                    source_type=source_type,
                    source_id=source_id,
                    path=path,
                    heading=heading,
                    title=title,
                    body=body,
                    related_ids=related,
                )
            )
    return documents


def ensure_search_fts(db: sqlite3.Connection) -> bool:
    try:
        db.execute(
            """
            create virtual table if not exists search_fts
            using fts5(doc_id unindexed, title, body, related_text)
            """
        )
        return True
    except sqlite3.OperationalError:
        return False


def clear_search_index(db: sqlite3.Connection, has_fts: bool) -> None:
    if has_fts:
        db.execute("delete from search_fts")
    db.execute("delete from search_graph_edges")
    db.execute("delete from search_vectors")
    db.execute("delete from search_documents")


def search_index_scope(include_raw_input: bool) -> str:
    return "with_raw_input" if include_raw_input else "default"


def search_index_lock_path() -> Path:
    return state_path("state", "search_index.lock")


@contextmanager
def search_index_lock(blocking: bool = False, timeout_seconds: float = 30.0):
    lock_path = search_index_lock_path()
    deadline = datetime.now().timestamp() + timeout_seconds
    acquired = False
    while True:
        try:
            lock_path.mkdir()
            acquired = True
            break
        except FileExistsError:
            try:
                age_seconds = datetime.now().timestamp() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age_seconds > 600:
                try:
                    lock_path.rmdir()
                    continue
                except OSError:
                    pass
            if not blocking or datetime.now().timestamp() >= deadline:
                break
            time.sleep(0.05)
    try:
        yield acquired
    finally:
        if acquired:
            try:
                lock_path.rmdir()
            except FileNotFoundError:
                pass


def search_source_signature(db: sqlite3.Connection, include_raw_input: bool) -> str:
    file_rows = []
    for path in context_files(include_raw_input):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        file_rows.append(
            {
                "path": path.relative_to(root()).as_posix(),
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
            }
        )
    table_queries = [
        ("runs", "select count(*), max(coalesce(ended_at, started_at, '')) from runs"),
        ("metrics", "select count(*), '' from metrics"),
        ("artifacts", "select count(*), '' from artifacts"),
        ("decisions", "select count(*), max(created_at) from decisions"),
        ("handoffs", "select count(*), max(created_at) from handoffs"),
        ("route_checks", "select count(*), max(created_at) from route_checks"),
        ("rules", "select count(*), max(updated_at) from rules"),
        ("topics", "select count(*), max(updated_at) from topics"),
        ("topic_events", "select count(*), max(created_at) from topic_events"),
        ("topic_evidence_links", "select count(*), max(created_at) from topic_evidence_links"),
        ("topic_plans", "select count(*), max(updated_at) from topic_plans"),
        ("topic_plan_items", "select count(*), max(updated_at) from topic_plan_items"),
    ]
    db_rows = []
    for name, query in table_queries:
        count, latest = db.execute(query).fetchone()
        db_rows.append({"table": name, "count": int(count), "latest": latest or ""})
    payload = {
        "include_raw_input": include_raw_input,
        "files": file_rows,
        "db": db_rows,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def search_index_meta(db: sqlite3.Connection, include_raw_input: bool) -> sqlite3.Row | None:
    return db.execute(
        "select * from search_index_meta where scope = ?",
        (search_index_scope(include_raw_input),),
    ).fetchone()


def search_index_is_fresh(db: sqlite3.Connection, include_raw_input: bool, source_signature: str) -> bool:
    meta = search_index_meta(db, include_raw_input)
    if meta is None:
        return False
    if meta["source_signature"] != source_signature:
        return False
    return db.execute("select count(*) from search_documents").fetchone()[0] > 0


def update_search_index_meta(
    db: sqlite3.Connection,
    include_raw_input: bool,
    source_signature: str,
    doc_count: int,
    edge_count: int,
    has_fts: bool,
) -> None:
    db.execute(
        """
        insert into search_index_meta (scope, indexed_at, source_signature, doc_count, edge_count, has_fts)
        values (?, ?, ?, ?, ?, ?)
        on conflict(scope) do update set
            indexed_at = excluded.indexed_at,
            source_signature = excluded.source_signature,
            doc_count = excluded.doc_count,
            edge_count = excluded.edge_count,
            has_fts = excluded.has_fts
        """,
        (
            search_index_scope(include_raw_input),
            now_iso(),
            source_signature,
            doc_count,
            edge_count,
            1 if has_fts else 0,
        ),
    )


def token_counts_json(tokens: list[str]) -> tuple[str, float]:
    counts = Counter(tokens)
    norm = math.sqrt(sum(value * value for value in counts.values()))
    return json.dumps(counts, ensure_ascii=False, sort_keys=True), norm


def load_token_counts(row: sqlite3.Row) -> Counter[str]:
    return Counter(json.loads(row["token_counts_json"]))


def insert_search_document(db: sqlite3.Connection, doc: SearchDocument, has_fts: bool, timestamp: str) -> None:
    tokens = search_tokens(f"{doc.title}\n{doc.body}\n{' '.join(doc.related_ids)}")
    counts_json, norm = token_counts_json(tokens)
    db.execute(
        """
        insert into search_documents (
            doc_id, source_type, source_id, path, heading, title, body, related_ids_json, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc.doc_id,
            doc.source_type,
            doc.source_id,
            str(display_relative_path(doc.path)),
            doc.heading,
            doc.title,
            doc.body,
            json.dumps(doc.related_ids, ensure_ascii=False),
            timestamp,
        ),
    )
    db.execute(
        "insert into search_vectors (doc_id, token_counts_json, token_norm) values (?, ?, ?)",
        (doc.doc_id, counts_json, norm),
    )
    if has_fts:
        expanded_body = f"{doc.body}\n{' '.join(tokens)}"
        db.execute(
            "insert into search_fts (doc_id, title, body, related_text) values (?, ?, ?, ?)",
            (doc.doc_id, doc.title, expanded_body, " ".join(doc.related_ids)),
        )


def add_graph_edge(
    db: sqlite3.Connection,
    source_doc_id: str,
    target_doc_id: str,
    relation_type: str,
    summary: str,
) -> None:
    if source_doc_id == target_doc_id:
        return
    db.execute(
        """
        insert or ignore into search_graph_edges (source_doc_id, target_doc_id, relation_type, summary)
        values (?, ?, ?, ?)
        """,
        (source_doc_id, target_doc_id, relation_type, summary),
    )


def build_search_graph(db: sqlite3.Connection, documents: list[SearchDocument]) -> None:
    by_source_id: dict[str, list[SearchDocument]] = {}
    for doc in documents:
        if doc.source_id and is_structured_search_id(doc.source_id):
            by_source_id.setdefault(doc.source_id, []).append(doc)
    for doc in documents:
        for related_id in doc.related_ids:
            for target in by_source_id.get(related_id, []):
                add_graph_edge(db, doc.doc_id, target.doc_id, "mentioned-id", f"{doc.source_id} mentions {related_id}")
    for decision in db.execute("select decision_id, evidence_run_ids_json from decisions").fetchall():
        for decision_doc in by_source_id.get(decision["decision_id"], []):
            for run_id in json.loads(decision["evidence_run_ids_json"]):
                for run_doc in by_source_id.get(run_id, []):
                    add_graph_edge(db, decision_doc.doc_id, run_doc.doc_id, "decision-evidence", f"{decision['decision_id']} evidence {run_id}")
    for link in db.execute("select topic_id, evidence_type, evidence_id from topic_evidence_links").fetchall():
        for topic_doc in by_source_id.get(link["topic_id"], []):
            for target_doc in by_source_id.get(link["evidence_id"], []):
                add_graph_edge(
                    db,
                    topic_doc.doc_id,
                    target_doc.doc_id,
                    "topic-evidence",
                    f"{link['topic_id']} linked {link['evidence_type']} {link['evidence_id']}",
                )


def rebuild_search_index(
    db: sqlite3.Connection,
    include_raw_input: bool = False,
    source_signature: str | None = None,
) -> tuple[int, int, bool]:
    if source_signature is None:
        source_signature = search_source_signature(db, include_raw_input)
    has_fts = ensure_search_fts(db)
    clear_search_index(db, has_fts)
    documents = collect_search_documents(include_raw_input)
    timestamp = now_iso()
    for doc in documents:
        insert_search_document(db, doc, has_fts, timestamp)
    build_search_graph(db, documents)
    edge_count = db.execute("select count(*) from search_graph_edges").fetchone()[0]
    update_search_index_meta(db, include_raw_input, source_signature, len(documents), edge_count, has_fts)
    return len(documents), edge_count, has_fts


def command_search_index(args: argparse.Namespace) -> int:
    with search_index_lock(blocking=True) as acquired:
        if not acquired:
            raise UserError("search index is locked by another process")
        with database() as db:
            doc_count, edge_count, has_fts = rebuild_search_index(db, args.include_raw_input)
    print(f"indexed search documents: {doc_count}")
    print(f"indexed graph edges: {edge_count}")
    print(f"raw_input: {'included' if args.include_raw_input else 'excluded'}")
    print(f"bm25_backend: {'sqlite_fts5' if has_fts else 'python_fallback'}")
    print("light_vector: local token vector")
    return 0


def fts_match_query(tokens: list[str]) -> str:
    unique = []
    seen = set()
    for token in tokens:
        cleaned = re.sub(r"[^\w]", "", token, flags=re.UNICODE)
        if len(cleaned) < 1 or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(f'"{cleaned}"')
        if len(unique) >= 32:
            break
    return " OR ".join(unique)


def bm25_search(db: sqlite3.Connection, query: str, limit: int) -> list[tuple[str, float]]:
    tokens = search_tokens(query)
    match_query = fts_match_query(tokens)
    if match_query and ensure_search_fts(db):
        try:
            rows = db.execute(
                """
                select doc_id, bm25(search_fts) as rank
                from search_fts
                where search_fts match ?
                order by rank
                limit ?
                """,
                (match_query, limit),
            ).fetchall()
            if rows:
                return [(row["doc_id"], -float(row["rank"])) for row in rows]
        except sqlite3.OperationalError:
            pass
    return python_bm25_search(db, tokens, limit)


def python_bm25_search(db: sqlite3.Connection, query_tokens: list[str], limit: int) -> list[tuple[str, float]]:
    if not query_tokens:
        return []
    vector_rows = db.execute("select * from search_vectors").fetchall()
    if not vector_rows:
        return []
    docs = [(row["doc_id"], load_token_counts(row), sum(load_token_counts(row).values())) for row in vector_rows]
    avg_len = sum(length for _doc_id, _counts, length in docs) / len(docs)
    query_terms = sorted(set(query_tokens))
    doc_freq: dict[str, int] = {}
    for term in query_terms:
        doc_freq[term] = sum(1 for _doc_id, counts, _length in docs if counts.get(term, 0) > 0)
    scores: list[tuple[str, float]] = []
    k1 = 1.2
    b = 0.75
    total_docs = len(docs)
    for doc_id, counts, doc_len in docs:
        score = 0.0
        for term in query_terms:
            freq = counts.get(term, 0)
            if freq <= 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
            denom = freq + k1 * (1 - b + b * (doc_len / avg_len if avg_len else 0))
            score += idf * ((freq * (k1 + 1)) / denom)
        if score > 0:
            scores.append((doc_id, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def light_vector_search(db: sqlite3.Connection, query: str, limit: int) -> list[tuple[str, float]]:
    query_counts = Counter(search_tokens(query))
    query_norm = math.sqrt(sum(value * value for value in query_counts.values()))
    if query_norm == 0:
        return []
    results: list[tuple[str, float]] = []
    for row in db.execute("select * from search_vectors").fetchall():
        doc_counts = load_token_counts(row)
        doc_norm = float(row["token_norm"])
        if doc_norm == 0:
            continue
        dot = sum(query_counts[token] * doc_counts.get(token, 0) for token in query_counts)
        score = dot / (query_norm * doc_norm)
        if score > 0:
            results.append((row["doc_id"], score))
    return sorted(results, key=lambda item: item[1], reverse=True)[:limit]


def graph_search(db: sqlite3.Connection, seed_doc_ids: list[str], query: str, limit: int) -> list[tuple[str, float]]:
    explicit_ids = set(extract_related_ids(query))
    if explicit_ids:
        rows = db.execute(
            "select doc_id from search_documents where source_id in ({})".format(
                ",".join("?" for _ in explicit_ids)
            ),
            tuple(explicit_ids),
        ).fetchall()
        seed_doc_ids.extend(row["doc_id"] for row in rows)
    seen = set(seed_doc_ids)
    results: list[tuple[str, float]] = []
    for seed in seed_doc_ids[:10]:
        edges = db.execute(
            """
            select source_doc_id, target_doc_id
            from search_graph_edges
            where source_doc_id = ? or target_doc_id = ?
            """,
            (seed, seed),
        ).fetchall()
        for edge in edges:
            target = edge["target_doc_id"] if edge["source_doc_id"] == seed else edge["source_doc_id"]
            if target in seen:
                continue
            seen.add(target)
            results.append((target, 1.0))
            if len(results) >= limit:
                return results
    return results


def fuse_search_results(
    bm25: list[tuple[str, float]],
    vector: list[tuple[str, float]],
    graph: list[tuple[str, float]],
    limit: int,
) -> list[tuple[str, float, dict[str, int]]]:
    streams = [("bm25", 0.55, bm25), ("light_vector", 0.30, vector), ("graph", 0.15, graph)]
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for name, weight, results in streams:
        for index, (doc_id, _score) in enumerate(results, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + weight * (1 / (SEARCH_FUSION_K + index))
            ranks.setdefault(doc_id, {})[name] = index
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    return [(doc_id, score, ranks[doc_id]) for doc_id, score in ordered]


def snippet(text: str, max_len: int = 180) -> str:
    flattened = " ".join(text.split())
    if len(flattened) <= max_len:
        return flattened
    return flattened[: max_len - 3] + "..."


def command_search_query(args: argparse.Namespace) -> int:
    stale_warning = False
    with database() as db:
        source_signature = search_source_signature(db, include_raw_input=False)
        fresh = search_index_is_fresh(db, include_raw_input=False, source_signature=source_signature)
    if not fresh:
        with search_index_lock(blocking=False) as acquired:
            if acquired:
                with database() as db:
                    current_signature = search_source_signature(db, include_raw_input=False)
                    if not search_index_is_fresh(db, include_raw_input=False, source_signature=current_signature):
                        rebuild_search_index(db, include_raw_input=False, source_signature=current_signature)
            else:
                stale_warning = True
    with database() as db:
        bm25_results = bm25_search(db, args.text, max(args.limit * 3, 20))
        vector_results = light_vector_search(db, args.text, max(args.limit * 3, 20))
        seeds = [doc_id for doc_id, _score in bm25_results[:5]]
        seeds.extend(doc_id for doc_id, _score in vector_results[:5] if doc_id not in seeds)
        graph_results = graph_search(db, seeds, args.text, max(args.limit * 2, 10))
        fused = fuse_search_results(bm25_results, vector_results, graph_results, args.limit)
        docs = {
            row["doc_id"]: row
            for row in db.execute(
                "select * from search_documents where doc_id in ({})".format(
                    ",".join("?" for _ in fused) if fused else "''"
                ),
                tuple(doc_id for doc_id, _score, _ranks in fused),
            ).fetchall()
        }
        total = db.execute("select count(*) from search_documents").fetchone()[0]
    print("# Search Results")
    print(f"query: {args.text}")
    print(f"indexed_documents: {total}")
    if stale_warning:
        print("warning: search index refresh is already running; results may not include recent writes")
    if not fused:
        print("no results")
        return 0
    for index, (doc_id, score, ranks) in enumerate(fused, start=1):
        doc = docs[doc_id]
        related_ids = ", ".join(json.loads(doc["related_ids_json"]))
        print(f"{index}. score={score:.6f} source={doc['source_type']} id={doc['source_id'] or 'none'}")
        print(f"   path: {doc['path']}")
        if doc["heading"]:
            print(f"   heading: {doc['heading']}")
        print(f"   title: {doc['title']}")
        if args.explain:
            signal_text = "; ".join(f"{name} rank={rank}" for name, rank in sorted(ranks.items()))
            print(f"   signals: {signal_text}")
        if related_ids:
            print(f"   related_ids: {related_ids}")
        if doc["heading"]:
            print(
                "   next: "
                f"auto-iter context show --path {shlex.quote(doc['path'])} --heading {shlex.quote(doc['heading'])}"
            )
        else:
            print(f"   next: inspect {doc['path']}")
        print(f"   snippet: {snippet(doc['body'])}")
    return 0


INTENT_RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "ownership-routing",
        ["AIT", "auto-iter", "auto_iteration", "update", "migrate", "search query", "handoff", "skill"],
        [
            "Before writing any plan, decide whether the request belongs to the managed project or to the AIT tool itself.",
            "If the request is about AIT itself, switch to the auto_iteration source repository and update AIT's own global plan, version tracking, or topic plan.",
            "Do not write AIT tool work into the managed project's project plan or topic plan.",
        ],
    ),
    (
        "planning",
        ["做个计划", "更新计划", "计划一下", "方案", "plan"],
        [
            "Check whether plans/active_plan.md or plans/version_iterations.md should change.",
            "If the request changes managed-project direction, update plans/project_plan.md first.",
            "If the request changes AIT tool capability scope, switch to the auto_iteration source repository and update AIT's global plan first.",
            "Do not record an experiment run only from a planning phrase.",
        ],
    ),
    (
        "pre-execution",
        ["执行吧", "实施吧", "确定执行", "开始跑", "先跑", "run it", "execute"],
        [
            "If this is an experiment route, run auto-iter route check before executing.",
            "Use auto-iter run exec only when config, dataset, command, metrics, and artifacts are clear.",
            "do not run or record only from this keyword; first confirm missing command inputs.",
        ],
    ),
    (
        "post-result",
        ["拿到结果", "跑完数据", "测试结束", "跑完了", "结果出来", "finished"],
        [
            "Collect metrics and artifact paths before writing final conclusions.",
            "Use auto-iter run finish if a manual run was started.",
            "Use auto-iter decision add after the conclusion is clear and evidence run_id is available.",
        ],
    ),
    (
        "mid-session-record",
        ["中途记录", "记录一下当前状态", "先保存当前状态", "做个阶段记录", "阶段记录", "保存当前接力点"],
        [
            "Run auto-iter checkpoint save --text \"<用户原话>\".",
            "Use the same state-save scope as session end before or during this checkpoint.",
            "do not commit or push unless the user explicitly asks.",
        ],
    ),
    (
        "topic-plan-carryover",
        ["计划", "方案", "下一步", "实施方向", "开发方向", "验收", "不做", "acceptance", "todo"],
        [
            "If the discussion created or accepted work that changes the current topic goal, non-goal, acceptance, or next tasks, persist it in the topic plan immediately.",
            "Use auto-iter topic plan set --topic-id <id> when the current topic goal, non-goal, or acceptance changed.",
            "Use auto-iter topic task add --topic-id <id> when concrete implementation or verification work was identified.",
            "Run auto-iter topic plan show --topic-id <id> and confirm the adopted plan is visible before checkpoint or handoff.",
        ],
    ),
    (
        "session-end-implementation-carryover",
        ["新 session", "下一 session", "下个 session", "新会话", "下一会话", "下个会话"],
        [
            "If the text names a next-session implementation direction, update the topic plan before handoff generate.",
            "Use auto-iter topic plan set --topic-id <id> when the current goal, non-goal, or acceptance changed.",
            "Use auto-iter topic task add --topic-id <id> for concrete next-session implementation work.",
            "Run auto-iter topic plan show --topic-id <id> and confirm the next-session direction appears before handoff generate.",
        ],
    ),
    (
        "session-end",
        ["结束当前 session", "做 handoff", "准备关", "关 session"],
        [
            "Run auto-iter handoff generate.",
            "Run auto-iter handoff validate.",
            "If the user asked to submit or push, commit relevant changes and push configured remotes.",
        ],
    ),
]


def command_intent_check(args: argparse.Namespace) -> int:
    text = args.text
    normalized = text.lower()
    matched: list[tuple[str, list[str]]] = []
    for intent, keywords, actions in INTENT_RULES:
        if any(keyword.lower() in normalized for keyword in keywords):
            matched.append((intent, actions))
    print("INTENT CHECKPOINT")
    print(f"text: {text}")
    if not matched:
        print("intent: none")
        print("- No checkpoint keyword matched. Continue normal reasoning.")
        return 0
    for intent, actions in matched:
        print(f"intent: {intent}")
        for action in actions:
            print(f"- {action}")
    return 0


def add_common_run_subcommands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    run_parser = subparsers.add_parser("run")
    run_sub = run_parser.add_subparsers(dest="run_command", required=True)
    start = run_sub.add_parser("start")
    start.add_argument("--config", required=True)
    start.add_argument("--dataset", required=True)
    start.add_argument("--command", required=True)
    start.add_argument("--seed")
    start.add_argument("--session")
    start.set_defaults(func=command_run_start)
    exec_cmd = run_sub.add_parser("exec")
    exec_cmd.add_argument("--config", required=True)
    exec_cmd.add_argument("--dataset", required=True)
    exec_cmd.add_argument("--command", required=True)
    exec_cmd.add_argument("--metrics")
    exec_cmd.add_argument("--artifact", action="append", default=[])
    exec_cmd.add_argument("--seed")
    exec_cmd.add_argument("--session")
    exec_cmd.set_defaults(func=command_run_exec)
    finish = run_sub.add_parser("finish")
    finish.add_argument("run_id")
    finish.add_argument("--status", required=True)
    finish.add_argument("--metrics")
    finish.add_argument("--artifact", action="append", default=[])
    finish.set_defaults(func=command_run_finish)
    list_cmd = run_sub.add_parser("list")
    list_cmd.add_argument("--latest", type=int, default=10)
    list_cmd.set_defaults(func=command_run_list)
    show = run_sub.add_parser("show")
    show.add_argument("run_id")
    show.set_defaults(func=command_run_show)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-iteration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("--legacy-layout", action="store_true", help="create project state in the pre-.auto_iter layout")
    init.set_defaults(func=command_init)
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--topic-id")
    doctor.set_defaults(func=command_doctor)
    migrate = subparsers.add_parser("migrate")
    migrate.add_argument("--layout", choices=["project-plan", SINGLE_DIR_LAYOUT], default="project-plan")
    migrate.set_defaults(func=command_migrate)
    install = subparsers.add_parser("install")
    install.add_argument("--bin-dir", default=str(default_bin_dir()))
    install.add_argument("--skills-dir", default=str(default_skills_dir()))
    install.set_defaults(func=command_install)
    uninstall = subparsers.add_parser("uninstall")
    uninstall.add_argument("--bin-dir", default=str(default_bin_dir()))
    uninstall.add_argument("--skills-dir", default=str(default_skills_dir()))
    project_state = uninstall.add_mutually_exclusive_group()
    project_state.add_argument("--keep-project-state", action="store_true")
    project_state.add_argument("--remove-project-state", action="store_true")
    uninstall.set_defaults(func=command_uninstall)
    update = subparsers.add_parser("update")
    update.add_argument("--bin-dir", default=str(default_bin_dir()))
    update.add_argument("--skills-dir", default=str(default_skills_dir()))
    update.add_argument("--check-project", action="store_true")
    update.set_defaults(func=command_update)
    project = subparsers.add_parser("project")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    project_link_topic = project_sub.add_parser("link-topic")
    project_link_topic.add_argument("--project-heading", required=True)
    project_link_topic.add_argument("--topic-id", required=True)
    project_link_topic.add_argument("--relation", choices=sorted(PROJECT_TOPIC_RELATIONS), default="related")
    project_link_topic.add_argument("--summary", default="")
    project_link_topic.set_defaults(func=command_project_link_topic)
    project_topic_links = project_sub.add_parser("topic-links")
    project_topic_links.add_argument("--project-heading", required=True)
    project_topic_links.set_defaults(func=command_project_topic_links)
    topic = subparsers.add_parser("topic")
    topic_sub = topic.add_subparsers(dest="topic_command", required=True)
    topic_current = topic_sub.add_parser("current")
    topic_current.set_defaults(func=command_topic_current)
    topic_list = topic_sub.add_parser("list")
    topic_list.set_defaults(func=command_topic_list)
    topic_show = topic_sub.add_parser("show")
    topic_show.add_argument("--topic-id", required=True)
    topic_show.set_defaults(func=command_topic_show)
    topic_link = topic_sub.add_parser("link")
    topic_link.add_argument("--topic-id")
    topic_link.add_argument("--allow-default-topic", action="store_true")
    topic_link.add_argument("--run-id", action="append", default=[])
    topic_link.add_argument("--decision-id", action="append", default=[])
    topic_link.add_argument("--artifact-id", action="append", default=[])
    topic_link.add_argument("--summary", default="")
    topic_link.set_defaults(func=command_topic_link)
    topic_evidence = topic_sub.add_parser("evidence")
    topic_evidence.add_argument("--topic-id", required=True)
    topic_evidence.add_argument("--latest", type=int, default=20)
    topic_evidence.set_defaults(func=command_topic_evidence)
    topic_project_links = topic_sub.add_parser("project-links")
    topic_project_links.add_argument("--topic-id", required=True)
    topic_project_links.set_defaults(func=command_topic_project_links)
    topic_start = topic_sub.add_parser("start")
    topic_start.add_argument("--title", required=True)
    topic_start.add_argument("--summary", default="")
    topic_start.add_argument("--current-goal", default="")
    topic_start.add_argument("--current-summary", default="")
    topic_start.set_defaults(func=command_topic_start)
    topic_switch = topic_sub.add_parser("switch")
    topic_switch.add_argument("--topic-id", required=True)
    topic_switch.add_argument("--current-summary", default="")
    topic_switch.set_defaults(func=command_topic_switch)
    topic_satisfy = topic_sub.add_parser("satisfy")
    topic_satisfy.add_argument("--summary", required=True)
    topic_satisfy.set_defaults(func=command_topic_satisfy)
    topic_board = topic_sub.add_parser("board")
    topic_board.set_defaults(func=command_topic_board)
    topic_plan = topic_sub.add_parser("plan")
    topic_plan_sub = topic_plan.add_subparsers(dest="topic_plan_command", required=True)
    topic_plan_set = topic_plan_sub.add_parser("set")
    topic_plan_set.add_argument("--topic-id")
    topic_plan_set.add_argument("--allow-default-topic", action="store_true")
    topic_plan_set.add_argument("--status", default="open")
    topic_plan_set.add_argument("--goal", default="")
    topic_plan_set.add_argument("--non-goal", action="append", default=[])
    topic_plan_set.add_argument("--acceptance", action="append", default=[])
    topic_plan_set.add_argument("--stop-condition", action="append", default=[])
    topic_plan_set.add_argument("--escalation-condition", action="append", default=[])
    topic_plan_set.set_defaults(func=command_topic_plan_set)
    topic_plan_show = topic_plan_sub.add_parser("show")
    topic_plan_show.add_argument("--topic-id", required=True)
    topic_plan_show.set_defaults(func=command_topic_plan_show)
    topic_plan_current = topic_plan_sub.add_parser("current")
    topic_plan_current.set_defaults(func=command_topic_plan_current)
    topic_task = topic_sub.add_parser("task")
    topic_task_sub = topic_task.add_subparsers(dest="topic_task_command", required=True)
    topic_task_add = topic_task_sub.add_parser("add")
    topic_task_add.add_argument("--topic-id")
    topic_task_add.add_argument("--allow-default-topic", action="store_true")
    topic_task_add.add_argument("--status", choices=sorted(TOPIC_TASK_STATUSES), default="todo")
    topic_task_add.add_argument("--title", required=True)
    topic_task_add.add_argument("--description", default="")
    topic_task_add.add_argument("--acceptance", default="")
    topic_task_add.add_argument("--evidence", action="append", default=[])
    topic_task_add.set_defaults(func=command_topic_task_add)
    topic_task_set = topic_task_sub.add_parser("set")
    topic_task_set.add_argument("--item-id", required=True)
    topic_task_set.add_argument("--status", choices=sorted(TOPIC_TASK_STATUSES), required=True)
    topic_task_set.add_argument("--evidence", action="append", default=[])
    topic_task_set.set_defaults(func=command_topic_task_set)
    topic_task_list = topic_task_sub.add_parser("list")
    topic_task_list.add_argument("--topic-id", required=True)
    topic_task_list.set_defaults(func=command_topic_task_list)
    add_common_run_subcommands(subparsers)
    rule = subparsers.add_parser("rule")
    rule_sub = rule.add_subparsers(dest="rule_command", required=True)
    rule_add = rule_sub.add_parser("add")
    rule_add.add_argument("--title", required=True)
    rule_add.add_argument("--claim", required=True)
    rule_add.add_argument("--source-kind", choices=sorted(RULE_SOURCE_KINDS), required=True)
    rule_add.add_argument("--rule-kind", choices=sorted(RULE_KINDS), required=True)
    rule_add.add_argument("--scope-kind", choices=sorted(RULE_SCOPE_KINDS), required=True)
    rule_add.add_argument("--status", choices=sorted(RULE_STATUSES), required=True)
    rule_add.add_argument("--supersedes-rule-id")
    rule_add.add_argument("--evidence", action="append", default=[])
    rule_add.add_argument("--note", action="append", default=[])
    rule_add.set_defaults(func=command_rule_add)
    rule_list = rule_sub.add_parser("list")
    rule_list.set_defaults(func=command_rule_list)
    rule_show = rule_sub.add_parser("show")
    rule_show.add_argument("rule_id")
    rule_show.set_defaults(func=command_rule_show)
    decision = subparsers.add_parser("decision")
    decision_sub = decision.add_subparsers(dest="decision_command", required=True)
    add = decision_sub.add_parser("add")
    add.add_argument("--status", required=True)
    add.add_argument("--evidence", action="append", default=[])
    add.add_argument("--title", required=True)
    add.add_argument("--claim", required=True)
    add.add_argument("--route-keyword", action="append", default=[])
    add.add_argument(
        "--route-relation",
        choices=["keyword", "method", "parameter-space", "supersedes"],
        default="keyword",
    )
    add.add_argument("--route-param", action="append", default=[])
    add.add_argument("--reopen-condition")
    add.add_argument("--supersedes")
    add.set_defaults(func=command_decision_add)
    supersede = decision_sub.add_parser("supersede")
    supersede.add_argument("old_id")
    supersede.add_argument("--by", dest="new_id", required=True)
    supersede.set_defaults(func=command_decision_supersede)
    route = subparsers.add_parser("route")
    route_sub = route.add_subparsers(dest="route_command", required=True)
    check = route_sub.add_parser("check")
    check.add_argument("--config", required=True)
    check.add_argument("--summary", required=True)
    check.set_defaults(func=command_route_check)
    handoff = subparsers.add_parser("handoff")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    generate = handoff_sub.add_parser("generate")
    generate.add_argument("--topic-id")
    generate.add_argument("--print-path", action="store_true", help="print generated handoff path for manual debugging")
    generate.set_defaults(func=command_handoff_generate)
    validate = handoff_sub.add_parser("validate")
    validate.add_argument("--topic-id")
    validate.set_defaults(func=command_handoff_validate)
    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint_sub = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    checkpoint_save = checkpoint_sub.add_parser("save")
    checkpoint_save.add_argument("--topic-id")
    checkpoint_save.add_argument("--text", required=True)
    checkpoint_save.set_defaults(func=command_checkpoint_save)
    context = subparsers.add_parser("context")
    context_sub = context.add_subparsers(dest="context_command", required=True)
    index = context_sub.add_parser("index")
    index.add_argument("--include-raw-input", action="store_true")
    index.set_defaults(func=command_context_index)
    show_context = context_sub.add_parser("show")
    show_context.add_argument("--path", required=True)
    show_context.add_argument("--heading", required=True)
    show_context.add_argument("--allow-raw-input", action="store_true")
    show_context.set_defaults(func=command_context_show)
    search = subparsers.add_parser("search")
    search_sub = search.add_subparsers(dest="search_command", required=True)
    search_index = search_sub.add_parser("index")
    search_index.add_argument("--include-raw-input", action="store_true")
    search_index.set_defaults(func=command_search_index)
    search_query = search_sub.add_parser("query")
    search_query.add_argument("--text", required=True)
    search_query.add_argument("--limit", type=int, default=10)
    search_query.add_argument("--explain", action="store_true")
    search_query.set_defaults(func=command_search_query)
    intent = subparsers.add_parser("intent")
    intent_sub = intent.add_subparsers(dest="intent_command", required=True)
    intent_check = intent_sub.add_parser("check")
    intent_check.add_argument("--text", required=True)
    intent_check.set_defaults(func=command_intent_check)
    resume = subparsers.add_parser("resume")
    resume.add_argument("--topic-id")
    resume.set_defaults(func=command_resume)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
