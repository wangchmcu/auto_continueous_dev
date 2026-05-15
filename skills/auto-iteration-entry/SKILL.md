---
name: auto-iteration-entry
description: Use when the user wants to continue, resume, or run a long-running algorithm iteration managed by auto_iteration, especially from Codex CLI, so the agent automatically calls auto-iter commands without asking the user to leave Codex or type absolute Python paths.
---

# Auto Iteration Entry

Use this skill as the Codex-side entry point for `auto_iteration`.

## Required Start

Run these commands in the current project root:

```bash
auto-iter doctor
auto-iter resume
```

Then read:

1. `plans/global_plan.md`
2. `plans/version_iterations.md`
3. `plans/active_plan.md`
4. `decisions/active/`
5. `decisions/rejected/`
6. `decisions/superseded/`

Do not read `raw_input/` by default. Read it only when starting a project for the first time or when later work explicitly needs missing information from original input. If useful information is found there, write it back into plans, decisions, handoff, or run summaries.

If `auto-iter` is missing, run:

```bash
python3 /home/ryan/auto_iteration/tools/auto_iter.py install
```

Then retry `auto-iter doctor`.

## Before A New Experiment Route

Run:

```bash
auto-iter route check --config <config.json> --summary "<中文路线说明>"
```

If the route check returns `BLOCKED`, do not run that route unless the user explicitly reopens it.

For rejected numeric parameter ranges, record the rejected decision with `--route-relation parameter-space --route-param name:min:max`.

## Loading Context

Before broad history reading, run:

```bash
auto-iter context index
```

Then load only the needed section:

```bash
auto-iter context show --path <file> --heading "<heading>"
```

Use `--include-raw-input` or `--allow-raw-input` only for initial project setup or explicit missing-information lookup.

## Running An Experiment

Prefer:

```bash
auto-iter run exec --config <config.json> --dataset <dataset-id> --command "<exact command>" --metrics <metrics.json> --artifact <artifact-path>
```

Use `run start` and `run finish` only when the experiment cannot be launched from one command.

## After Results

Record conclusions with evidence:

```bash
auto-iter decision add --status <active|rejected|open> --evidence <run_id> --title "<中文标题>" --claim "<中文结论>"
```

Use `--route-keyword` and `--reopen-condition` for rejected routes.

## End Of Task

Run:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

Final response must report:

- current version
- what changed in this task
- what remains inside the current version
- what global plan capabilities remain outside the current version
