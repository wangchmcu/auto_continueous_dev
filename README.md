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

Make sure `/home/ryan/.local/bin` is on `PATH` before expecting `auto-iter` to be found by a shell or Codex-launched command. If it is not on `PATH`, the installer prints a `path hint`; agents should use the printed absolute command path instead of asking the user to type it.

To remove the installed command and Codex skills without deleting any project
tracking state:

```bash
auto-iter uninstall
```

`uninstall` removes the installed `auto-iter` wrapper and installed Codex skills
only. It does not remove project directories such as `state/`, `plans/`,
`topics/`, `raw_input/`, `decisions/`, `runs/`, or `handoffs/`.

In an interactive terminal, uninstall asks whether to remove those project
state directories too and prints a short description of what each directory
stores. In non-interactive runs, project state is kept by default; use
`--keep-project-state` or `--remove-project-state` when the choice should be
explicit.

## Topic archive

Topic archive keeps only one current issue or direction in default context.
The active topic is projected to `topics/active_topic.md`; archived topics are
listed in `topics/index.md` and stored under `topics/archive/`.

```bash
auto-iter topic start --title "Topic Archive MVP" --summary "按 topic 归档并按需恢复上下文"
auto-iter topic current
auto-iter topic list
auto-iter topic switch --topic-id <id> --current-summary "当前现场摘要"
auto-iter topic satisfy --summary "阶段性达到预期"
```

Starting or switching topics archives the previous active topic as
`archived_open`. `topic satisfy` archives the current topic as
`archived_satisfied`; that means the current expectation is satisfied, not that
the topic can never be reopened. If an agent only suspects that the user has
changed topic semantically, it should ask “是不是已经切入新的 topic 了？” before
running a topic switch command.

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

`auto-iter init` is intentionally low-assumption. It creates the state store and
tracking files, but it must not invent a business roadmap for the target project.
The generated plans start with the project's goal marked as pending user input.

If initialization happens in the middle of an existing Codex conversation, the
agent should create a bootstrap checkpoint after init. The checkpoint is a
structured summary of confirmed facts, user-confirmed goals, exposed workflow
problems, open questions, and candidate checks. Candidate checks inferred by the
agent must stay marked as unaccepted until the user confirms them.

Initial setup should also inspect `raw_input/` as a possible source of original
materials:

```bash
auto-iter context index --include-raw-input
```

If `raw_input/` has files, the agent reads only relevant sections with
`--allow-raw-input`, labels recovered facts as `raw_input_source`, and writes
useful information back into tracking. If it is empty, initialization simply
continues with the empty directory. `auto-iter init` itself does not ingest raw
input automatically.

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

For natural-language stage changes, the agent should first run an intent checkpoint（意图检查点）. It is a reminder command: it prints what the agent should check next, but it does not write state, start experiments, or create conclusions by itself.

```bash
auto-iter intent check --text "<用户原话>"
```

Typical use:

- User says “做个计划” or “更新计划”：the agent checks whether `plans/active_plan.md`, `plans/version_iterations.md`, or `plans/global_plan.md` should change.
- User says “执行吧”, “实施吧”, or “确定执行”：the agent checks whether `route check` is needed and whether config, dataset, command, metrics, and artifacts are clear enough for `run exec`.
- User says “拿到结果了”, “跑完数据了”, or “测试结束了”：the agent checks metrics, artifacts, and evidence `run_id` before writing a decision.
- User says “中途记录一下”, “先保存当前状态”, or “做个阶段记录”：the agent saves the current handoff checkpoint without ending the session and without committing or pushing unless explicitly requested.
- User says “结束当前 session” or “做 handoff”：the agent generates and validates handoff, then commits and pushes if requested.

For a mid-session record, the agent uses the same state-save scope as session end, but the user does not need to name internal files or commands:

```bash
auto-iter checkpoint save --text "<用户原话>"
```

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

If the concrete problem also shows that the self improve workflow itself is
insufficient, the agent should treat that as a second-order self improve item in
the same run when feasible. If it is too large to complete immediately, it must
be added to the plan files as an explicit pending item.

## Good Examples

### Planning or execution checkpoint

User says in Codex CLI:

```text
先更新计划，然后确定执行。
```

The agent should:

- run `auto-iter intent check --text "先更新计划，然后确定执行。"`
- update the relevant plan files if scope or task state changed
- run `auto-iter route check --config <config.json> --summary "<中文路线说明>"` before an experiment route
- use `auto-iter run exec` only when config, dataset, command, metrics, and artifacts are clear

The user does not need to type the `intent check` command. It is the agent's implementation detail.

### Recording completed results

User says in Codex CLI:

```text
跑完数据了，拿到结果了。
```

The agent should:

- run `auto-iter intent check --text "跑完数据了，拿到结果了。"`
- collect metrics and artifact paths
- identify the evidence `run_id`
- write the reusable conclusion with `auto-iter decision add`

The checkpoint is not a replacement for the decision record. It only reminds the agent what evidence must exist before writing the decision.

### Recording progress mid-session

User says in Codex CLI:

```text
中途记录一下当前状态。
```

The agent should:

- run `auto-iter intent check --text "中途记录一下当前状态。"`
- update any needed tracking records using the same state-save scope as session end
- run `auto-iter checkpoint save --text "中途记录一下当前状态。"`
- continue the same Codex session

The agent should not ask the user which internal file to update. The agent should not commit or push unless the user explicitly asks.

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

`raw_input/` stores original input materials or old project imports. It is only for first project setup or explicit missing-information lookup. During first setup, index it with `auto-iter context index --include-raw-input`; read only relevant sections with `--allow-raw-input`. Normal work should use `plans/`, `handoffs/`, `decisions/`, run summaries, and `state/agent_state.db` first. If useful information is recovered from `raw_input/`, label it as `raw_input_source` and write it back into tracking information.

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
