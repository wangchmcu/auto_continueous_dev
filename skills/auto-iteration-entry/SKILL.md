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
- “之前是不是说过某个现象”, “我记得之前好像提过”, or another fuzzy historical-memory question：run `auto-iter search query --text "<用户原话>" --limit 10 --explain`, then use the returned path, heading, `run_id`, `decision_id`, or topic evidence to load the exact source. The search command is a recall helper, not a replacement for evidence.
- “从 raw_input 查缺失信息”：use raw input only for initial setup or explicit missing-information lookup, then write any useful recovered information back into plans, decisions, handoff, or run summaries.
- “auto it self improve”：use the `auto-it-self-improve` skill. This is the fixed trigger for generalizing a solved concrete problem into a reusable auto_iteration system improvement.
- “更新 AIT”, “刷新 AIT”, or “update AIT”：run `auto-iter update` to refresh the installed command wrapper and Codex skills without running `init` or touching project state.
- “卸载 AIT”, “卸载 auto-iter”, or “重新安装 AIT”：run the install management workflow. `auto-iter uninstall` removes installed command and Codex skills only; it does not remove project state.
- “开启 topic”, “切换 topic”, “回到某个 topic”, or “当前 topic 达到预期”：run the topic archive workflow below.
- If the prompt only seems semantically different from the current topic, do not guess or switch automatically. Ask the user: “是不是已经切入新的 topic 了？” Only after the user confirms, run `auto-iter topic start` or `auto-iter topic switch`.
- If the user asks for new context-management, history-retrieval, topic-management, or evidence-linking capabilities, first inspect `plans/version_iterations.md` sections for current-version remaining gaps and future-version direction. If the request matches an existing `global plan backlog` item, continue that route and do not start a separate plan branch.
- Planning, execution, result, or session-end phrases such as “做个计划”, “更新计划”, “执行吧”, “实施吧”, “确定执行”, “拿到结果了”, “跑完数据了”, or “测试结束了”：first run `auto-iter intent check --text "<用户原话>"`. This is an intent checkpoint（意图检查点）：it prints the next checks the agent should do, but it does not directly write state or run experiments.
- “中途记录一下”, “先保存当前状态”, “做个阶段记录”, or a similar mid-session record request：treat this as a black-box save request. Run `auto-iter checkpoint save --text "<用户原话>"`. Use the same state-save scope as session end, but do not end the session, commit, or push unless the user explicitly asks.

## Required Start

Run these commands in the current project root. If the shell is already inside
a subdirectory of an initialized AIT project, `auto-iter` finds the nearest
parent directory with `state/agent_state.db` and uses that parent as the project
root; do not rerun `init` merely because the current shell is nested.

```bash
auto-iter doctor
auto-iter resume
```

Then read:

1. `handoffs/latest_handoff.md`, especially `Current Baseline`（当前基线：当前被承认为继续开发起点的版本、方法、结果和证据入口）
2. `plans/global_plan.md`
3. `plans/version_iterations.md`
4. `plans/active_plan.md`
5. `topics/active_topic.md` if it exists
6. decision entries listed by `auto-iter context index`

If the generated handoff read order includes a project-root `AGENTS.md`, read it
as project-specific Codex process rules. If it is not listed, do not invent or
require it; `auto-iter init` does not create project-root `AGENTS.md`.

If more detail is needed, use `auto-iter context index` first and then `auto-iter context show --path <file> --heading "<heading>"` for only the needed section. If `context index` reports an orphan or stale decision projection, do not treat that Markdown file as current context; SQLite is the factual source.

Do not read `raw_input/` by default. Read it only when starting a project for the first time or when later work explicitly needs missing information from original input. If useful information is found there, write it back into plans, decisions, handoff, or run summaries.

## New Project Initialization

When initializing a target project, keep the initialization low-assumption:

```bash
auto-iter init
auto-iter doctor
auto-iter context index --include-raw-input
```

`auto-iter init` creates state and low-assumption tracking templates. It does not
authorize the agent to invent a roadmap for the target project. Do not convert
README observations or agent guesses into formal versions unless the user has
confirmed them.

During initial setup, treat `raw_input/` as a possible bootstrap input source.
If it has no files, continue with the empty directory. If it has files, inspect
the index first, then read only relevant raw input sections with
`auto-iter context show --path <file> --heading "<heading>" --allow-raw-input`.
Do not automatically ingest or summarize the whole directory.

If init happens after the Codex conversation already contains useful context,
perform a bootstrap checkpoint:

1. Summarize confirmed facts, user-confirmed goals, exposed problems, open questions, and candidate checks.
2. Include relevant existing raw input as `raw_input_source` when it was actually read.
3. Update the tracking files with source labels such as `user_confirmed`, `repo_observed`, `raw_input_source`, `conversation_summary`, `agent_inferred`, and `proposed_not_accepted`.
4. Keep `agent_inferred` and `proposed_not_accepted` items out of formal version routes.
5. Run `auto-iter checkpoint save --text "<用户原话或bootstrap说明>"`.

If `auto-iter` is missing, install from the AIT source checkout with the
platform-appropriate Python command:

```text
Windows Codex app: py -m auto_iteration.cli install
Windows Codex app fallback: python -m auto_iteration.cli install
WSL/Linux Codex CLI: python3 -m auto_iteration.cli install
macOS Codex app: python3 -m auto_iteration.cli install
```

Then retry `auto-iter doctor`. If the command is installed but the shell still
prints `command not found`, do not stop or ask the user to type the path. Use
the installed absolute command path printed by install. On Windows this is
usually an `auto-iter.cmd` wrapper; on WSL/Linux and macOS it is usually an
`auto-iter` wrapper. Continue the same workflow from the current project root.
The installer should prefer an operating-system-appropriate command directory
that is already on `PATH` and writable. If it falls back to a user-owned
directory and prints a path hint, use the printed absolute command path rather
than editing shell startup files without explicit user opt-in.

## Install Management

To remove installed AIT command and Codex skills without deleting project
tracking state, run:

```bash
auto-iter uninstall
```

This removes the installed `auto-iter` wrapper and installed skills only. It
does not remove project state such as `state/`, `plans/`, `topics/`, `raw_input/`,
`decisions/`, `runs/`, or `handoffs/`.

When a terminal is interactive, uninstall asks whether to remove project state
too and briefly explains what each directory stores. In non-interactive runs,
project state is kept unless explicitly requested. Use:

```bash
auto-iter uninstall --keep-project-state
auto-iter uninstall --remove-project-state
```

Only use `--remove-project-state` when the user confirms that local tracking
documents, topic projections, raw inputs, decisions, runs, and handoffs can be deleted.

To refresh the installed wrapper and Codex skills while always preserving
project state, run:

```bash
auto-iter update
```

`auto-iter update` removes the command wrapper and installed skills owned by the
current AIT checkout, then installs fresh copies. It does not run `init`, does
not create `state/`, `plans/`, `topics/`, `raw_input/`, `decisions/`, `runs/`,
or `handoffs/`, and it never prompts about deleting project state. It accepts
the same `--bin-dir` and `--skills-dir` options as install and uninstall. Use
`auto-iter update --check-project` only when the current directory should be
checked after refresh; if no AIT project state exists, the project check is
skipped and `init` is not run.

To reinstall after uninstall, use the same platform-appropriate install command
from the AIT source checkout:

```text
Windows Codex app: py -m auto_iteration.cli install
WSL/Linux Codex CLI or macOS Codex app: python3 -m auto_iteration.cli install
```

## Topic Archive

Topic archive keeps one default topic for ordinary recovery. The default topic
is the old `active` topic compatibility path; it is not the only topic a Codex
thread may work on. Commands that support topic resolution use this order:
explicit `--topic-id`, then `AUTO_ITER_TOPIC_ID`, then the default topic.
Run `auto-iter doctor` to inspect the resolved topic before writing records.

Use these commands:

```bash
auto-iter topic current
auto-iter topic list
auto-iter topic show --topic-id <id>
auto-iter topic start --title "<标题>" --summary "<新 topic 摘要>" --current-summary "<当前现场摘要>"
auto-iter topic switch --topic-id <id> --current-summary "<当前现场摘要>"
auto-iter topic satisfy --summary "<阶段性达到的预期>"
auto-iter topic link --topic-id <id> --run-id <run_id> --decision-id <decision_id> --artifact-id <artifact_id> --summary "<中文证据摘要>"
auto-iter topic evidence --topic-id <id>
auto-iter topic plan set --topic-id <id> --goal "<目标>" --non-goal "<不做什么>" --acceptance "<验收标准>"
auto-iter topic plan show --topic-id <id>
auto-iter topic plan current
auto-iter topic task add --topic-id <id> --title "<任务>" --description "<说明>" --acceptance "<验收>"
auto-iter topic task set --item-id <item-id> --status <todo|doing|done|blocked|dropped>
auto-iter topic task list --topic-id <id>
auto-iter topic board
auto-iter handoff generate --topic-id <id>
auto-iter handoff validate --topic-id <id>
auto-iter checkpoint save --topic-id <id> --text "<用户原话>"
auto-iter migrate
```

Rules:

- There can be at most one default topic in the old `active` slot.
- Starting or switching the default topic archives the previous default topic as `archived_open`.
- `archived_open` means archived but still open; switching back should continue work.
- `archived_satisfied` means the current expectation is satisfied, not permanently finished; switching back reopens it.
- Multi-thread work should prefer explicit `--topic-id` or `AUTO_ITER_TOPIC_ID` instead of switching the default topic just to record one topic.
- If more than one topic is open, topic-scoped write commands must use explicit `--topic-id`, `AUTO_ITER_TOPIC_ID`, or `--allow-default-topic`.
- If a new prompt only looks like a new topic semantically, ask “是不是已经切入新的 topic 了？” before running any topic switch command.
- New sessions read `handoffs/latest_handoff.md` and `topics/active_topic.md`; archived topic files under `topics/archive/` are loaded only on demand.
- When a topic has clear supporting evidence, link the relevant run, decision, or artifact with `auto-iter topic link` so future sessions can use `auto-iter topic evidence` instead of manually searching all history.
- When a topic starts to carry local planning work, use `auto-iter topic plan set/show/current`; keep topic tasks and acceptance checks in topic plan, while final claims still go through `decision add` with evidence.
- Use `auto-iter topic task add/set/list` for topic-local task status. Marking a task done does not replace `decision add` or `topic link`.
- Use `auto-iter topic board` for the cross-topic project view; keep per-topic detail in topic plan, topic handoff, and topic board instead of global plan.
- Use topic-scoped handoff or checkpoint commands when separate Codex threads work on separate topics. They write `topics/<topic_id>/latest_handoff.md`.
- Use `auto-iter migrate` after upgrading an old project so legacy topics get empty topic plans and refreshed projections.

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

For fuzzy historical-memory questions, use the local search layer first:

```bash
auto-iter search query --text "<用户原话>" --limit 10 --explain
```

`search query` refreshes the default tracking-information index before searching. The search layer combines BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）and graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）. After search returns candidates, load the exact source with `context show`, `run show`, or `topic evidence`.

## Running An Experiment

Prefer:

```bash
auto-iter run exec --config <config.json> --dataset <dataset-id> --command "<exact command>" --metrics <metrics.json> --artifact <artifact-path>
```

`run exec` launches `<exact command>` from the resolved AIT project root. If the
actual experiment must execute in a subdirectory, put the directory change in
the command itself, for example:

```bash
--command "cd path/to/workdir && python experiment.py"
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

## Mid-Session Record

When the user wants to save progress without ending the session, run:

```bash
auto-iter checkpoint save --text "<用户原话>"
```

This uses the same state-save scope as the end-of-task workflow, but it does not mean the current Codex session is ending. Do not commit or push unless the user explicitly asks.

The user should not need to name internal files such as `active_plan`, `version_iterations`, decisions, or handoff. Choose and update the needed internal records yourself, then save the checkpoint.

## End Of Task

Run:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

`auto-iter handoff generate` is silent by default so hook stdout stays empty while the handoff is still written. Use `auto-iter handoff generate --print-path` only for manual debugging. Do not use shell redirection for this because the same hook should work on Windows, WSL/Linux, and macOS.

If the user also asks to submit, save, or push the work, check git status, commit the relevant changes, and push using the repository's configured remote. Do not leave uncommitted auto-iteration changes unless the user explicitly asks to keep them local.

Final response must report:

- current version
- what changed in this task
- what remains inside the current version
- what global plan capabilities remain outside the current version
