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
   - If the concrete problem shows that the self improve workflow itself cannot fully express or complete the improvement, record that as a second-order improvement requirement in the same run.
   - A second-order improvement means the process for improving AIT also needs to change, not only the target workflow being improved.
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

## Second-Order Improvements

When self improve exposes a limitation in the self improve workflow itself, do not stop at documenting the limitation.

Handle it as part of the same improvement when feasible:

- name the second-order limitation explicitly
- update this skill if the workflow needs a new step, guardrail, or report item
- update README or entry skills if users need different trigger wording
- update CLI templates or tests if the limitation affects generated state
- report what part was completed now and what part remains for a later iteration

If the second-order improvement is too large to complete in the same run, add it to the plan files as an explicit pending item rather than hiding it in the final prose.

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
- second-order self improve limitation, if any, and how it was handled
- files changed and why
- concrete details intentionally excluded
- verification commands and results
