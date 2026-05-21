---
name: auto-iteration
description: Use when working on long-running algorithm experiments that must preserve parameters, metrics, decisions, rejected routes, and session handoff state across Codex sessions.
---

# Auto Iteration Workflow

Use this skill to keep long-running algorithm iteration recoverable across sessions.

## Natural Language Triggers

- If the user says “继续这个 auto-iteration 项目” or “接着上个 session”, run the required start workflow.
- If the user says “结束当前 session” or “做 handoff”, run the end-of-session workflow.
- If the user asks to “查阅某个结论、实验、参数或历史细节”, run `auto-iter context index`, choose the relevant file and heading, then run `auto-iter context show --path <file> --heading "<heading>"`.
- If the user asks a fuzzy historical-memory question such as “之前是不是说过某个现象”, run `auto-iter search query --text "<用户原话>" --limit 10 --explain`, then load the exact source from the returned path, heading, `run_id`, `decision_id`, or topic evidence.
- If the user asks to search `raw_input/`, do it only for initial setup or explicit missing-information lookup, then write useful information back into tracking information.
- If the user says “auto it self improve”, use the `auto-it-self-improve` skill to generalize the solved concrete problem into a reusable auto_iteration system improvement.
- If the user says a planning, execution, result, or session-end phrase such as “做个计划”, “更新计划”, “执行吧”, “实施吧”, “确定执行”, “拿到结果了”, “跑完数据了”, or “测试结束了”, first run `auto-iter intent check --text "<用户原话>"`. This is an intent checkpoint（意图检查点）：it prints the next checks the agent should do, but it does not directly write state or run experiments.
- If the user says “中途记录一下”, “先保存当前状态”, “做个阶段记录”, or a similar mid-session record request, treat it as a black-box save request. Run `auto-iter checkpoint save --text "<用户原话>"`. Use the same state-save scope as session end, but do not end the session, commit, or push unless the user explicitly asks.

## Required Start

1. Check the local state:

```bash
auto-iter doctor
```

If the shell is inside a subdirectory of an initialized AIT project, `auto-iter`
finds the nearest parent directory with `state/agent_state.db` and uses that
parent as the project root. Do not rerun `init` just because the current shell
is nested under an existing project.

2. Restore the latest handoff when present:

```bash
auto-iter resume
```

3. Read `handoffs/latest_handoff.md` first, especially `Current Baseline`（当前基线：当前被承认为继续开发起点的版本、方法、结果和证据入口）, then read `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`.

4. Run `auto-iter context index` before reading decisions. Read only decision projections listed by the index; if it reports orphan or stale projections, do not treat those Markdown files as current context.

5. Do not read `raw_input/` by default. Read it only when starting a project for the first time or when later work explicitly needs missing information from original input. Anything useful found there must be written back into tracking information.

If the generated handoff read order includes project-root `AGENTS.md`, read it
as project-specific Codex process rules. If it is not listed, do not invent or
require it; `auto-iter init` does not create project-root `AGENTS.md`.

For first project setup, inspect possible raw input with:

```bash
auto-iter context index --include-raw-input
```

If `raw_input/` has files, read only relevant sections with
`auto-iter context show --path <file> --heading "<heading>" --allow-raw-input`.
Do not ingest the whole directory. Mark recovered information as
`raw_input_source` before writing it back into tracking information.

If `auto-iter` is missing, install it from the AIT source checkout with the
platform-appropriate Python command:

```text
Windows Codex app: py -m auto_iteration.cli install
Windows Codex app fallback: python -m auto_iteration.cli install
WSL/Linux Codex CLI: python3 -m auto_iteration.cli install
macOS Codex app: python3 -m auto_iteration.cli install
```

To remove the installed command and Codex skills without deleting project
tracking state, run:

```bash
auto-iter uninstall
```

The uninstall command does not remove `state/`, `plans/`, `topics/`, `raw_input/`,
`decisions/`, `runs/`, or `handoffs/`.

In an interactive terminal, uninstall asks whether to remove those project state
directories too and prints a short description of each directory. In
non-interactive runs, use `--keep-project-state` or `--remove-project-state` to
make the choice explicit.

Install should prefer an operating-system-appropriate command directory already
on `PATH` and writable. If it falls back to a user-owned directory, use the
printed absolute command path; do not edit shell startup files unless the user
explicitly opts in.

## Topic Archive

Use topic archive when the user wants to keep only one current issue/direction
in default context and load older work on demand.

```bash
auto-iter topic current
auto-iter topic list
auto-iter topic show --topic-id <id>
auto-iter topic start --title "<标题>" --summary "<新 topic 摘要>" --current-summary "<当前现场摘要>"
auto-iter topic switch --topic-id <id> --current-summary "<当前现场摘要>"
auto-iter topic satisfy --summary "<阶段性达到的预期>"
auto-iter topic link --topic-id <id> --run-id <run_id> --decision-id <decision_id> --artifact-id <artifact_id> --summary "<中文证据摘要>"
auto-iter topic evidence --topic-id <id>
```

Rules:

- There is at most one `active` topic.
- Non-current topics are archived as `archived_open` or `archived_satisfied`.
- `archived_satisfied` means stage expectations are met; it can still be reopened.
- When a prompt only seems to change topic semantically, ask “是不是已经切入新的 topic 了？” before switching.
- Read `topics/active_topic.md` by default; load `topics/archive/` only on user request or confirmed topic switch.
- Link clear supporting runs, decisions, and artifacts with `auto-iter topic link`; inspect the evidence chain later with `auto-iter topic evidence`.

## Before A New Experiment

If the user phrase is only “执行吧”, “实施吧”, “确定执行”, or a similar execution approval, first run:

```bash
auto-iter intent check --text "<用户原话>"
```

Then continue only when the concrete config, dataset, command, metrics, and artifact expectations are clear.

Run a route check before executing the experiment:

```bash
auto-iter route check --config <config.json> --summary "<中文路线说明>"
```

If the command returns `BLOCKED`, do not run that route unless the user explicitly reopens it.

For rejected numeric parameter ranges, record the rejected decision with:

```bash
auto-iter decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-relation parameter-space --route-param name:min:max
```

## Loading Context

Before broad history reading, use:

```bash
auto-iter context index
```

Load only the section needed:

```bash
auto-iter context show --path <file> --heading "<heading>"
```

Use `--include-raw-input` or `--allow-raw-input` only for initial project setup or explicit missing-information lookup.

For fuzzy historical-memory questions, search before broad manual reading:

```bash
auto-iter search query --text "<用户原话>" --limit 10 --explain
```

`search query` refreshes the default tracking-information index before searching. This local search combines BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）and graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）. Treat the result as a candidate list only; confirm the answer from `context show`, `run show`, `decision` projection, or `topic evidence`.

## Recording A Run

Prefer `run exec` when the experiment can be launched from one shell command. It records the run, executes the command, captures stdout/stderr/debug logs, and generates summaries:

```bash
auto-iter run exec --config <config.json> --dataset <dataset-id> --command "<exact command>" --metrics <metrics.json> --artifact <artifact-path>
```

`run exec` launches `<exact command>` from the resolved AIT project root. If the
actual experiment must execute in a nested working directory, include that
directory change inside the command, for example:

```bash
--command "cd path/to/workdir && python experiment.py"
```

Use `run start` and `run finish` when the experiment must be launched manually.

Start the manual run record before the experiment:

```bash
auto-iter run start --config <config.json> --dataset <dataset-id> --command "<exact command>"
```

Finish the run record after the experiment:

```bash
auto-iter run finish <run_id> --status success --metrics <metrics.json> --artifact <artifact-path>
```

Use `failed` or `aborted` instead of `success` when the run did not complete.

## Recording A Decision

If the user says “拿到结果了”, “跑完数据了”, “测试结束了”, or a similar result-complete phrase, first run:

```bash
auto-iter intent check --text "<用户原话>"
```

Then collect metrics, artifacts, and the evidence `run_id` before writing a decision.

Every conclusion needs a decision with evidence:

```bash
auto-iter decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-keyword "<关键词>"
```

Decision status meanings:

- `active`: currently valid conclusion.
- `rejected`: tested and should not be repeated.
- `superseded`: replaced by a newer conclusion.
- `open`: not yet decided; only a minimum validation experiment is allowed.

## Mid-Session Record

When the user wants to save progress without ending the session, run:

```bash
auto-iter checkpoint save --text "<用户原话>"
```

This uses the same state-save scope as the end-of-session workflow, but it does not mean the current Codex session is ending. Do not commit or push unless the user explicitly asks.

The user should not need to name internal files such as `active_plan`, `version_iterations`, decisions, or handoff. Choose and update the needed internal records yourself, then save the checkpoint.

## End Of Session

Generate the next-session entry point:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

`auto-iter handoff generate` is silent by default for Codex hook parsing. Use `auto-iter handoff generate --print-path` only for manual debugging. Do not use platform-specific shell redirection for this, so the hook remains compatible with Windows, WSL/Linux, and macOS.

The generated `handoffs/latest_handoff.md` should be the first document a fresh session reads unless the handoff read order lists an existing project-root `AGENTS.md` before it.

When implementation scope changes, update `plans/global_plan.md` if the global capability set changes, then update `plans/version_iterations.md` so the next session can see the current version tasks.

Before ending a task, report the current version, what changed in this task, what remains inside the current version, and what global capabilities remain outside the current version. Use `global plan` to mean the full long-running algorithm iteration context-management plan.
