# auto_iteration

`auto_iteration` is a local state manager for long-running Codex-assisted algorithm experiments.

The goal is to stop treating chat history as project state. Experiment facts go into SQLite, readable summaries go into Markdown, and fresh Codex sessions resume from a generated handoff.

## Primary Codex Workflow

Install once from this repository:

```bash
cd /home/ryan/auto_iteration
python3 -m auto_iteration.cli install
```

The install command creates:

- command: `/home/ryan/.local/bin/auto-iter`
- Codex entry skill: `~/.codex/skills/auto-iteration-entry`
- system-improvement skill: `~/.codex/skills/auto-it-self-improve`

The install command also runs a self-check. It verifies that `python3` is available, `auto-iter` is executable, and the required skills have non-empty `SKILL.md` files. A healthy install prints `install check: ok`.

Make sure `/home/ryan/.local/bin` is on `PATH` before expecting `auto-iter` to be found by a shell or Codex-launched command.

Then start Codex from the target algorithm project:

```bash
cd /path/to/algorithm_repo
codex
```

In Codex CLI, ask the agent to use auto-iteration:

```text
Use auto-iteration for this project. If this is a new project, initialize it first. Then run doctor, resume, context index, and continue from the current plans and decisions.
```

`auto-iteration` is the fixed tool and workflow name. It does not change with the target algorithm project. The part that changes per project is the directory you start Codex from, such as `/path/to/algorithm_repo`.

The agent should call `auto-iter` inside the same Codex session. You do not need to exit Codex to run the commands manually.

For a new project, the agent initializes the project root:

```bash
auto-iter init
```

For an existing project, the agent starts with:

```bash
auto-iter doctor
auto-iter resume
auto-iter context index
```

## Manual CLI Workflow

Manual commands are for installation, debugging, CI, or cases where you intentionally operate outside Codex CLI.

Inside this repository, this works:

```bash
python3 -m auto_iteration.cli init
```

In another algorithm repository, use the installed command from the target project root:

```bash
cd /path/to/algorithm_repo
auto-iter init
auto-iter doctor
```

If `auto-iter` is not installed yet, run the wrapper once:

```bash
python3 /home/ryan/auto_iteration/tools/auto_iter.py install
```

## What The Agent Calls

Before a new experiment route:

```bash
auto-iter route check --config config.json --summary "<中文路线说明>"
```

Record a run by letting `auto_iteration` execute the command and capture logs:

```bash
auto-iter run exec --config config.json --dataset demo --command "python experiment.py" --metrics metrics.json --artifact report.md
```

Record a rejected route with evidence from the completed run:

```bash
auto-iter decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-keyword "<关键词>"
```

Block a rejected numeric parameter range:

```bash
auto-iter decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-relation parameter-space --route-param threshold:0.60:0.90
```

Generate and validate handoff:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

## Codex Entry

The Codex entry is the installed skill `auto-iteration-entry`.

It is installed by:

```bash
python3 -m auto_iteration.cli install
```

The source lives in this repository at `skills/auto-iteration-entry/`. The installed copy goes to `~/.codex/skills/auto-iteration-entry`, or `$CODEX_HOME/skills/auto-iteration-entry` when `CODEX_HOME` is set.

In Codex CLI, ask to continue an auto-iteration task; the agent should use that entry skill and call `auto-iter` commands inside the same Codex session.

## Auto It Self Improve

`auto it self improve` is a fixed trigger phrase. It does not run automatically.

Use it after a concrete auto_iteration workflow problem has been solved and you want the agent to generalize that lesson back into the system:

```text
auto it self improve：把刚才解决的问题抽象成通用规则，更新 auto_iteration 系统。不要把本项目的具体路径、数据集、一次性参数或临时文件名写进系统规则。
```

The agent should use the installed `auto-it-self-improve` skill, choose the appropriate files to update, add tests when generated templates or installation behavior changes, and report which concrete details were intentionally excluded.

## Good Examples

### Ending a long session

User says in Codex CLI:

```text
结束当前 session。请生成并校验 handoff，提交并推送当前工作。
```

The agent should:

- run `auto-iter handoff generate`
- run `auto-iter handoff validate`
- check git status
- commit relevant changes
- push to the configured remote when requested
- report the current version, completed work, current-version remaining work, and remaining global plan capabilities

### Starting a new session

User starts Codex from the same algorithm project:

```bash
cd /path/to/algorithm_repo
codex
```

Then says:

```text
继续这个 auto-iteration 项目，使用 auto-iteration-entry 恢复上下文。
```

Here `auto-iteration` and `auto-iteration-entry` are fixed names. Do not replace them with the algorithm project's name.

The agent should:

- run `auto-iter doctor`
- run `auto-iter resume`
- run `auto-iter context index`
- read `plans/global_plan.md`, `plans/version_iterations.md`, `plans/active_plan.md`, and the relevant decisions
- avoid `raw_input/` unless this is initial setup or explicit missing-information lookup
- summarize current goal, active decisions, rejected routes, and next minimum experiment

### Looking up details

User says:

```text
查一下上次为什么否定高阈值区间，不要一次性读全部历史。
```

The agent should:

- run `auto-iter context index`
- choose the relevant decision, run summary, or handoff section
- run `auto-iter context show --path <file> --heading "<heading>"`
- answer from that section and cite the file path it used

The user should not need to write the full `context show` command. The command is the agent's implementation detail.

## Version Task Tracking

Use `plans/global_plan.md` as the global plan and `plans/version_iterations.md` as the version-level task tracker. The version tracker records each version's goal, task checklist, acceptance checks, evidence, and next-version direction.

Before changing implementation scope, update:

```bash
sed -n '1,220p' plans/global_plan.md
sed -n '1,220p' plans/version_iterations.md
sed -n '1,160p' plans/active_plan.md
```

At session end, regenerate the handoff so the next Codex session sees the current version state:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

## Raw Input

`raw_input/` stores original input materials or old project imports. It is only for first project setup or explicit missing-information lookup. Normal work should use `plans/`, `handoffs/`, `decisions/`, run summaries, and `state/agent_state.db` first. If useful information is recovered from `raw_input/`, write it back into tracking information.

## Context Loading

Use the context index before reading broad history:

```bash
auto-iter context index
auto-iter context show --path plans/global_plan.md --heading "Global Plan"
```

`raw_input/` is excluded by default. Use `--include-raw-input` or `--allow-raw-input` only for initial project setup or explicit missing-information lookup.

## Storage Rule

- `state/agent_state.db`: factual source for runs, metrics, artifacts, decisions, route checks, and handoffs.
- `decisions/`: readable decision projections.
- `handoffs/latest_handoff.md`: fresh-session entry point.
- `raw_input/`: original input materials and old project imports.
- `plans/global_plan.md`: global plan for the full context-management system.
- `plans/version_iterations.md`: version-level task tracker.
- `plans/active_plan.md`: current engineering direction.
- `skills/auto-iteration-entry/SKILL.md`: Codex entry skill installed by `auto-iter install`.
- `skills/auto-it-self-improve/SKILL.md`: explicit-trigger skill for generalizing solved workflow problems into reusable system improvements.
- `runs/<run_id>/config_resolved.json`: resolved config snapshot.
- `runs/<run_id>/summary.md`: per-run readable summary.
- `runs/<run_id>/logs/stdout.log`: captured stdout.
- `runs/<run_id>/logs/stderr.log`: captured stderr.
- `runs/<run_id>/logs/debug.jsonl`: structured execution events.
- `runs/<run_id>/logs/error_summary.md`: bounded stderr summary for default reading.

`run_id` is an internal evidence handle generated by `auto-iter`. Developers do not need to memorize it. The agent should use the `run_id` printed by `run exec`, `run start`, `run list`, or `run show` when recording decisions. Humans only need to mention a `run_id` when they want to point at one specific historical experiment.
