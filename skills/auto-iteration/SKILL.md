---
name: auto-iteration
description: Use when working on long-running algorithm experiments that must preserve parameters, metrics, decisions, rejected routes, and session handoff state across Codex sessions.
---

# Auto Iteration Workflow

Use this skill to keep long-running algorithm iteration recoverable across sessions.

## Required Start

1. Check the local state:

```bash
python3 -m auto_iteration.cli doctor
```

2. Restore the latest handoff when present:

```bash
python3 -m auto_iteration.cli resume
```

3. Read `plans/version_iterations.md` and `plans/active_plan.md`.

4. Read `decisions/active/`, `decisions/rejected/`, and `decisions/superseded/` before proposing a new route.

## Before A New Experiment

Run a route check before executing the experiment:

```bash
python3 -m auto_iteration.cli route check --config <config.json> --summary "<中文路线说明>"
```

If the command returns `BLOCKED`, do not run that route unless the user explicitly reopens it.

## Recording A Run

Start the run record before the experiment:

```bash
python3 -m auto_iteration.cli run start --config <config.json> --dataset <dataset-id> --command "<exact command>"
```

Finish the run record after the experiment:

```bash
python3 -m auto_iteration.cli run finish <run_id> --status success --metrics <metrics.json> --artifact <artifact-path>
```

Use `failed` or `aborted` instead of `success` when the run did not complete.

## Recording A Decision

Every conclusion needs a decision with evidence:

```bash
python3 -m auto_iteration.cli decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-keyword "<关键词>"
```

Decision status meanings:

- `active`: currently valid conclusion.
- `rejected`: tested and should not be repeated.
- `superseded`: replaced by a newer conclusion.
- `open`: not yet decided; only a minimum validation experiment is allowed.

## End Of Session

Generate the next-session entry point:

```bash
python3 -m auto_iteration.cli handoff generate
```

The generated `handoffs/latest_handoff.md` should be the first document a fresh session reads after `AGENTS.md`.

When implementation scope changes, update `plans/version_iterations.md` before ending the session so the next session can see the current version tasks.
