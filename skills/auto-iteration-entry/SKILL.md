---
name: auto-iteration-entry
description: Use when the user wants to continue, resume, end, hand off, inspect details, or run a long-running algorithm iteration managed by auto_iteration, especially from Codex CLI, so the agent automatically calls auto-iter commands without asking the user to leave Codex or type absolute Python paths.
---

# Auto Iteration Entry

Use this skill as the Codex-side entry point for `auto_iteration`.

## Natural Language Triggers

When the user says one of these plain-language requests, treat it as a request to run the matching workflow. Do not ask the user to type the commands.

- `auto-iteration` and `auto-iteration-entry` are fixed tool and skill names. They do not change with the target algorithm project's name.
- “继续这个 auto-iteration 项目” or “接着上个 session”：run the required start workflow below.
- “结束当前 session” or “做 handoff”：run the end-of-task workflow below.
- “查阅某个结论、实验、参数或历史细节”：run `auto-iter context index`, choose the relevant file and heading, then run `auto-iter context show --path <file> --heading "<heading>"`.
- “从 raw_input 查缺失信息”：use raw input only for initial setup or explicit missing-information lookup, then write any useful recovered information back into plans, decisions, handoff, or run summaries.
- “auto it self improve”：use the `auto-it-self-improve` skill. This is the fixed trigger for generalizing a solved concrete problem into a reusable auto_iteration system improvement.
- Planning, execution, result, or session-end phrases such as “做个计划”, “更新计划”, “执行吧”, “实施吧”, “确定执行”, “拿到结果了”, “跑完数据了”, or “测试结束了”：first run `auto-iter intent check --text "<用户原话>"`. This is an intent checkpoint（意图检查点）：it prints the next checks the agent should do, but it does not directly write state or run experiments.

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

If more detail is needed, use `auto-iter context index` first and then `auto-iter context show --path <file> --heading "<heading>"` for only the needed section.

Do not read `raw_input/` by default. Read it only when starting a project for the first time or when later work explicitly needs missing information from original input. If useful information is found there, write it back into plans, decisions, handoff, or run summaries.

If `auto-iter` is missing, run:

```bash
python3 /home/ryan/auto_iteration/tools/auto_iter.py install
```

Then retry `auto-iter doctor`.

## Before A New Experiment Route

If the user phrase is only “执行吧”, “实施吧”, “确定执行”, or a similar execution approval, first run:

```bash
auto-iter intent check --text "<用户原话>"
```

Then continue only when the concrete config, dataset, command, metrics, and artifact expectations are clear.

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

When the user asks for detail in plain language, choose the file and heading yourself from the index. For example, “查一下上次为什么否定高阈值区间” should lead to the relevant rejected decision or run summary, not a request for the user to provide a full `context show` command.

## Running An Experiment

Prefer:

```bash
auto-iter run exec --config <config.json> --dataset <dataset-id> --command "<exact command>" --metrics <metrics.json> --artifact <artifact-path>
```

Use `run start` and `run finish` only when the experiment cannot be launched from one command.

## After Results

If the user says “拿到结果了”, “跑完数据了”, “测试结束了”, or a similar result-complete phrase, first run:

```bash
auto-iter intent check --text "<用户原话>"
```

Then collect metrics, artifacts, and the evidence `run_id` before writing a decision.

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

If the user also asks to submit, save, or push the work, check git status, commit the relevant changes, and push using the repository's configured remote. Do not leave uncommitted auto-iteration changes unless the user explicitly asks to keep them local.

Final response must report:

- current version
- what changed in this task
- what remains inside the current version
- what global plan capabilities remain outside the current version
