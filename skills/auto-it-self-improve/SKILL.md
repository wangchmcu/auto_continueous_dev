---
name: auto-it-self-improve
description: Use only when the user explicitly says "auto it self improve" and wants a resolved concrete auto_iteration workflow problem abstracted into a general system improvement without copying project-specific details into the system.
---

# Auto It Self Improve

Use this skill only when the user explicitly says `auto it self improve`.

## Purpose

Convert a resolved concrete problem into a general auto_iteration improvement. The concrete problem is evidence, not the rule.

## Workflow

1. Restate the concrete problem that was solved.
2. Extract the general problem shape.
3. Choose the system files that should change:
   - User-facing usage confusion: README.
   - Agent behavior or trigger wording: `skills/auto-iteration-entry/` or `skills/auto-iteration/`.
   - Stable process rules: `AGENTS.md`.
   - CLI behavior or generated project templates: `auto_iteration/cli.py` plus tests.
   - Version scope or future capability: `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`.
   - Session recovery behavior: handoff template code and handoff validation tests.
4. Patch the selected files with generalized content.
5. When the improvement changes a CLI command, generated template, installed skill, or user-facing workflow, update the matching plan files too: `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`.
6. Add or update tests when generated templates, installation, CLI behavior, or contamination checks are affected.
7. If skills changed, run the install command so the installed Codex skills match the repository source.
8. Run verification, then generate and validate handoff.

## Contamination Guard

Do not write concrete project details into the general system.

Forbidden as system rules:

- concrete project names
- concrete dataset names
- one-off parameter values
- private absolute paths from the user's project
- temporary filenames
- one-time troubleshooting details
- specific conversation wording that only applies once

Allowed as system rules:

- generalized trigger wording
- placeholder examples
- reusable file-selection rules
- workflow steps
- validation checks
- CLI or template behavior

## Required Report

Every run must report:

- concrete issue used as evidence
- generalized issue added to the system
- files changed and why
- concrete details intentionally excluded
- verification commands and results
