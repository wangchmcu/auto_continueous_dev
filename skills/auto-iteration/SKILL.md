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
- If the user asks to search `raw_input/`, do it only for initial setup or explicit missing-information lookup, then write useful information back into tracking information.

## Required Start

1. Check the local state:

```bash
auto-iter doctor
```

2. Restore the latest handoff when present:

```bash
auto-iter resume
```

3. Read `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`.

4. Read `decisions/active/`, `decisions/rejected/`, and `decisions/superseded/` before proposing a new route.

5. Do not read `raw_input/` by default. Read it only when starting a project for the first time or when later work explicitly needs missing information from original input. Anything useful found there must be written back into tracking information.

If `auto-iter` is missing, install it:

```bash
python3 /home/ryan/auto_iteration/tools/auto_iter.py install
```

## Before A New Experiment

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

## Recording A Run

Prefer `run exec` when the experiment can be launched from one shell command. It records the run, executes the command, captures stdout/stderr/debug logs, and generates summaries:

```bash
auto-iter run exec --config <config.json> --dataset <dataset-id> --command "<exact command>" --metrics <metrics.json> --artifact <artifact-path>
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

Every conclusion needs a decision with evidence:

```bash
auto-iter decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-keyword "<关键词>"
```

Decision status meanings:

- `active`: currently valid conclusion.
- `rejected`: tested and should not be repeated.
- `superseded`: replaced by a newer conclusion.
- `open`: not yet decided; only a minimum validation experiment is allowed.

## End Of Session

Generate the next-session entry point:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

The generated `handoffs/latest_handoff.md` should be the first document a fresh session reads after `AGENTS.md`.

When implementation scope changes, update `plans/global_plan.md` if the global capability set changes, then update `plans/version_iterations.md` so the next session can see the current version tasks.

Before ending a task, report the current version, what changed in this task, what remains inside the current version, and what global capabilities remain outside the current version. Use `global plan` to mean the full long-running algorithm iteration context-management plan.
