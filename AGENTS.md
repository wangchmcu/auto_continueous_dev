# Auto Iteration Agent Rules

## Communication

- 普通讨论使用中文；代码、命令、字段名和文件名保持英文。
- 不要裸写自造实验名、缩写或参数标签。必须使用时，紧接着解释中文含义、对应代码或数据位置、每个数字或字母参数的含义。
- 实验结果、参数对比、方案排序等包含数字列时，不使用普通 Markdown pipe table；改用对齐代码块或普通列表。
- 每次结束任务前，最终回复必须报告当前版本号、本次完成了哪些、当前版本内部还剩哪些、当前版本整体距离 `global plan` 还有哪些全局能力未覆盖。这里的 `global plan` 暂时指整个长周期算法迭代上下文管理方案，不只指当前版本。

## Before Any Coding Or Experiment

1. Run `auto-iter doctor` and read the result. If `auto-iter` is unavailable, run `python3 /home/ryan/auto_iteration/tools/auto_iter.py install` first.
2. Run `auto-iter resume` if `handoffs/latest_handoff.md` exists.
3. Read `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`.
4. Read active decisions under `decisions/active/`.
5. Before proposing or running a new experiment route, run:

```bash
auto-iter route check --config <config.json> --summary "<中文路线说明>"
```

6. Do not retry routes marked `rejected` or `superseded` unless the user explicitly reopens them.

## Version Task Tracking

- `plans/version_iterations.md` is the version-level task tracker.
- `plans/global_plan.md` is the global plan for the whole long-running algorithm iteration context-management system.
- Every version entry must include the version name, status, goal, task checklist, acceptance checks, and next-version direction.
- Every version entry must include a `global plan` distance section that states which global capabilities the current version covers and which global capabilities remain outside the current version.
- When a task status changes, update `plans/version_iterations.md` in the same change.
- Keep changing experiment history out of `AGENTS.md`; link to runs, decisions, artifacts, and plan files instead.

## Context Loading

- Use `auto-iter context index` before reading broad history.
- Use `auto-iter context show --path <file> --heading "<heading>"` to load only the needed section.
- Do not use `--include-raw-input` or `--allow-raw-input` unless the task is initial project setup or an explicit missing-information lookup.

## Natural Language Entry

- If the user says “结束当前 session” or “做 handoff”, run `auto-iter handoff generate` and `auto-iter handoff validate`; if the user asks to submit or push, also commit and push the relevant changes.
- If the user says “继续这个 auto-iteration 项目” or “接着上个 session”, run `auto-iter doctor`, `auto-iter resume`, and `auto-iter context index`, then restore context from plans, decisions, and run summaries.
- If the user asks to inspect a historical detail, choose the relevant file and heading from `auto-iter context index`, then run `auto-iter context show --path <file> --heading "<heading>"`; do not ask the user to provide the full command.

## Raw Input

- `raw_input/` stores original input materials or old project imports.
- Read `raw_input/` only when starting a project for the first time or when later work explicitly needs missing information from the original input.
- Normal work should read tracking information first: `plans/`, `handoffs/`, `decisions/`, run summaries, and `state/agent_state.db`.
- If `raw_input/` conflicts with tracking information, treat tracking information as newer unless the user explicitly asks to verify against the original input.
- Any useful information found in `raw_input/` must be written back into tracking information so future sessions do not need to rediscover it.

## Experiment Protocol

- Every experiment must have one `run_id`.
- Every experiment must save resolved config, metrics, logs, and artifacts.
- Every conclusion must become a decision record with evidence run IDs.
- For rejected parameter ranges, use `decision add --route-relation parameter-space --route-param name:min:max`.
- Raw logs stay under `runs/<run_id>/logs/`; do not paste full logs into context by default.
- Read summaries, metrics, artifacts, and decisions first; read raw logs only for a specific failure investigation.
- At session end, generate a handoff with:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

## State Ownership

- SQLite database `state/agent_state.db` is the factual source for runs, metrics, artifacts, decisions, route checks, and handoff records.
- Markdown files under `decisions/` and `handoffs/` are readable projections for humans and Codex.
- Markdown files under `plans/` track version-level implementation work and current engineering direction.
- `AGENTS.md` stores stable process rules only. Do not put changing experiment history here.
