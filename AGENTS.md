# Auto Iteration Agent Rules

## Communication

- 普通讨论使用中文；代码、命令、字段名和文件名保持英文。
- 不要裸写自造实验名、缩写或参数标签。必须使用时，紧接着解释中文含义、对应代码或数据位置、每个数字或字母参数的含义。
- 实验结果、参数对比、方案排序等包含数字列时，不使用普通 Markdown pipe table；改用对齐代码块或普通列表。
- 每次结束任务前，最终回复必须报告当前版本号、本次完成了哪些、当前版本内部还剩哪些、当前版本整体距离 `global plan` 还有哪些全局能力未覆盖。这里的 `global plan` 在 AIT 源仓指整个长周期算法迭代上下文管理方案；在被接管项目里，`plans/global_plan.md` 只是兼容入口，项目长期计划改读 `plans/project_plan.md`。

## Before Any Coding Or Experiment

1. Run `auto-iter doctor` and read the result. If `auto-iter` is unavailable, install from the AIT source checkout with the platform-appropriate Python command: Windows Codex app uses `py -m auto_iteration.cli install` or `python -m auto_iteration.cli install`; WSL/Linux Codex CLI and macOS Codex app use `python3 -m auto_iteration.cli install` or `python -m auto_iteration.cli install`.
2. Run `auto-iter resume` if `.auto_iter/handoffs/latest_handoff.md` or legacy `handoffs/latest_handoff.md` exists.
3. Read `.auto_iter/plans/project_plan.md` and `.auto_iter/plans/project_record_rules.md` when they exist, then read `.auto_iter/plans/global_plan.md`, `.auto_iter/plans/version_iterations.md`, and `.auto_iter/plans/active_plan.md`. Legacy projects may still use root-level `plans/`. In a managed project, `project_plan.md` is the project direction, `project_record_rules.md` is project-specific AIT recording rules, and `global_plan.md` is a compatibility entry. In the AIT source repository, root-level `plans/global_plan.md` remains AIT's own tool-level global plan when the source repo itself is still on legacy layout.
4. Read decisions through `auto-iter context index` and `auto-iter context show`; do not treat Markdown files under `decisions/` as current context if `context index` reports them as orphan or stale projections.
5. If the shell is nested inside an initialized AIT project, `auto-iter` should resolve the nearest parent containing `.auto_iter/state/agent_state.db` or legacy `state/agent_state.db` as the project root. Confirm both `root` and `state_dir` from `auto-iter doctor` before recording runs from a nested shell.
6. In Git worktree or multi-window work, set `AUTO_ITER_PROJECT_ROOT` or global `--project-root` to the shared AIT project root, and set `AUTO_ITER_WORKDIR` or `--workdir` to the current workdir（working directory: the directory where experiment commands actually run）. Confirm `root`, `state_dir`, `workdir`, and `workdir_source` from `auto-iter doctor`.
7. Before proposing or running a new experiment route, run:

```bash
auto-iter route check --config <config.json> --summary "<中文路线说明>"
```

8. Do not retry routes marked `rejected` or `superseded` unless the user explicitly reopens them.

## Version Task Tracking

- `plans/version_iterations.md` is the version-level task tracker.
- In the AIT source repository, `plans/global_plan.md` is the global plan for the whole long-running algorithm iteration context-management system.
- In a managed project, `plans/project_plan.md` is the project-level long-term plan and `plans/project_record_rules.md` is the project-level AIT recording rule file; `plans/global_plan.md` remains only as a compatibility entry for older workflows.
- Every version entry must include the version name, status, goal, task checklist, acceptance checks, and next-version direction.
- Every version entry must include a `global plan` distance section that states which global capabilities the current version covers and which global capabilities remain outside the current version.
- When a task status changes, update `plans/version_iterations.md` in the same change.
- Keep changing experiment history out of `AGENTS.md`; link to runs, decisions, artifacts, and plan files instead.

## Context Loading

- Use `auto-iter context index` before reading broad history.
- Use `auto-iter context show --path <file> --heading "<heading>"` to load only the needed section.
- If the user asks a fuzzy memory question such as “之前是不是说过某个现象”, first run `auto-iter search query --text "<用户原话>" --limit 10 --explain`. This command refreshes the default tracking-information index only when indexed inputs have changed; otherwise it reuses the existing index for a read-only search. Search is only a recall helper; after it finds a candidate, load the exact source with `context show` or the matching `run_id`、`decision_id`、topic evidence command.
- Before changing code in an existing topic or adjacent work area, run a topic evidence carryover check: inspect `auto-iter topic evidence --topic-id <id>` plus topic handoff/search results for prior fixes, rejected paths, and known pitfalls, then verify the current branch or worktree still contains any relevant fix. The topic plan alone is not enough; it is planning state, not the evidence chain.
- `auto-iter search index` builds the local recall index from tracking information. It uses BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）.
- Do not use `--include-raw-input` or `--allow-raw-input` unless the task is initial project setup or an explicit missing-information lookup.

## Natural Language Entry

- If initializing AIT in a target project, keep it low-assumption: `auto-iter init` creates state and pending tracking templates only. Do not convert README observations or agent guesses into formal roadmap items unless the user confirms them.
- During target project initialization, run `auto-iter context index --include-raw-input` after init/doctor. If `raw_input/` has files, read only relevant sections with `auto-iter context show --path <file> --heading "<heading>" --allow-raw-input`, then write useful information back into tracking with the `raw_input_source` label. If it has no files, continue with the empty directory.
- If initialization happens in the middle of an existing conversation, create a bootstrap checkpoint: summarize confirmed facts, user-confirmed goals, exposed problems, open questions, and candidate checks with source labels. Keep `agent_inferred` and `proposed_not_accepted` items out of formal version routes.
- If the user says “中途记录一下”, “先保存当前状态”, “做个阶段记录”, or a similar mid-session record request, treat it as a black-box save request. Run `auto-iter checkpoint save --text "<用户原话>"`. Use the same state-save scope as session end, but do not end the session, commit, or push unless the user explicitly asks.
- If the user says a planning, execution, result, or session-end phrase such as “做个计划”, “更新计划”, “执行吧”, “实施吧”, “确定执行”, “拿到结果了”, “跑完数据了”, or “测试结束了”, first run `auto-iter intent check --text "<用户原话>"`. This is an intent checkpoint（意图检查点）：it prints the next checks the agent should do, but it does not directly write state or run experiments.
- If the user reports a rejected experiment（被拒绝的实验：已经证明不能继续采用或不能合入的实验结果）, first run `auto-iter intent check --text "<用户原话>"`. If no `run_id` exists because the result came from an external tool or old Codex session, record it with `auto-iter run import`, then write `auto-iter decision add --status rejected` with `route-keyword` and `reopen-condition`.
- If `intent check` prints `ownership-routing`, treat it as 需求归属判断：before writing any plan, decide whether the request belongs to the managed project or to the AIT tool itself. If it is AIT tool work, switch to the auto_iteration source repository and update AIT's own `plans/global_plan.md`, `plans/version_iterations.md`, or topic plan. Do not write AIT tool work into the managed project's project plan or topic plan.
- If the user says “结束当前 session” or “做 handoff”, run `auto-iter handoff generate` and `auto-iter handoff validate`; if the user asks to submit or push, also commit and push the relevant changes.
- If the user says “继续这个 auto-iteration 项目” or “接着上个 session”, run `auto-iter doctor`, `auto-iter resume`, and `auto-iter context index`, then restore context from plans, decisions, and run summaries.
- If the user asks to inspect a historical detail, choose the relevant file and heading from `auto-iter context index`, then run `auto-iter context show --path <file> --heading "<heading>"`; do not ask the user to provide the full command.
- If the user asks a fuzzy historical-memory question, run `auto-iter search query --text "<用户原话>" --limit 10 --explain` before broad manual reading. Use the search result to choose the exact `context show` path, `run show`, `decision` projection, or `topic evidence` query.
- If the user says “auto it self improve”, use the `auto-it-self-improve` skill. This trigger is explicit; do not run system-improvement work automatically. If the improvement exposes a limitation in the self improve workflow itself, handle that as a second-order improvement or record it as an explicit pending plan item.
- If the user asks to update or refresh installed AIT, use `auto-iter update`; it refreshes the installed command wrapper and Codex skills, does not run `init`, does not create project state, and never prompts to delete project state. Use `auto-iter update --check-project` only when the user wants the current directory checked after the refresh.
- After AIT has been updated in an old managed project, use the old project migration runbook: `auto-iter update --check-project`, `auto-iter doctor`, `auto-iter migrate`, `auto-iter migrate --layout single-dir`, `auto-iter doctor`, `auto-iter context index`, `auto-iter handoff generate`, and `auto-iter handoff validate`. Do not run `init` for an already initialized old project.
- If the user asks to uninstall or reinstall AIT, use `auto-iter uninstall` for installed command and skill removal. In interactive use, let the uninstall prompt ask whether to remove project state directories and explain what they contain. In non-interactive use, pass `--keep-project-state` unless the user explicitly asks to delete project state; only then use `--remove-project-state`.
- Install should prefer an operating-system-appropriate command directory already on `PATH` and writable. If none exists, install into a user-owned fallback and print a path hint; do not edit shell startup files or mutate the user's environment without an explicit user opt-in.
- If the user explicitly says “开启 topic”, “切换 topic”, “回到某个 topic”, or “当前 topic 达到预期”, use `auto-iter topic current/list/show/start/switch/satisfy` as appropriate. If the prompt only semantically appears to move to a new issue or direction, first ask “是不是已经切入新的 topic 了？” and switch only after the user confirms.
- Treat the old `active topic` as the default topic for ordinary recovery, not as the only topic that can be worked on. Topic resolution order is explicit `--topic-id`, then `AUTO_ITER_TOPIC_ID`, then default topic. Use `auto-iter doctor` to confirm the resolved topic before writing records.
- Use `auto-iter topic plan set/show/current` for topic-local goals, non-goals, acceptance checks, stop conditions, and escalation conditions. Topic plan is planning state only; claims still require `decision add` with run evidence.
- Use `auto-iter topic task add/set/list` for topic-local todo, doing, done, blocked, and dropped items. Task state does not replace decisions or topic evidence links.
- Use `auto-iter topic board` for the cross-topic project view. It writes `.auto_iter/topics/board.md` in single-directory projects; do not move per-topic task detail into `plans/global_plan.md`.
- Use `auto-iter project link-topic --project-heading <heading> --topic-id <id> --relation <relation> --summary <summary>` when a topic explicitly serves a `project_plan.md` heading. This is bidirectional tracking, not automatic synchronization: `project_plan.md` remains the project-level plan, and topic plan remains the topic-local execution plan.
- In multi-thread work, use `auto-iter handoff generate --topic-id <id>` and `auto-iter checkpoint save --topic-id <id> --text "<text>"` for topic-scoped state so one thread does not overwrite another thread's topic handoff.
- If more than one topic is open, topic-scoped write commands must use explicit `--topic-id`, `AUTO_ITER_TOPIC_ID`, or `--allow-default-topic`; do not silently rely on the default topic.
- Use `auto-iter init` for a repository that has never been managed by AIT; reserve `auto-iter migrate` for upgrading an older AIT-managed project.
- Use `auto-iter migrate` after upgrading an old project so legacy topics get empty topic plans, refreshed topic projections, and the project plan split (`plans/project_plan.md`, `plans/project_record_rules.md`, plus a compatibility `plans/global_plan.md`). Use `auto-iter migrate --layout single-dir` when an old root-level AIT state layout should be moved under `.auto_iter/`.
- If a topic has clear supporting evidence, link it explicitly with `auto-iter topic link --topic-id <id> --run-id <run_id> --decision-id <decision_id> --artifact-id <artifact_id> --summary "<中文证据摘要>"`; inspect linked evidence with `auto-iter topic evidence --topic-id <id>`.
- If the user proposes new context-management, history-retrieval, topic-management, or evidence-linking capabilities, first inspect `plans/version_iterations.md` sections for current-version remaining gaps and future-version direction. If the request matches an existing `global plan backlog` item, continue that route and do not start a separate plan branch.
- If the user states, tightens, loosens, or deprecates an explicit workflow rule that should survive the current session, record it with `auto-iter rule add`, and use `--supersedes-rule-id <RL-...>` when replacing an older rule. Use `auto-iter rule list` and `rules/current_effective.md` to inspect the current effective rule set.

## Raw Input

- `.auto_iter/raw_input/` stores original input materials or old project imports; legacy projects may still use root-level `raw_input/`.
- Read raw input only when starting a project for the first time or when later work explicitly needs missing information from the original input.
- Initial project setup should index raw input, not ingest it wholesale.
- Normal work should read tracking information first: `.auto_iter/plans/`, `.auto_iter/handoffs/`, `.auto_iter/decisions/`, run summaries, and `.auto_iter/state/agent_state.db` when the project uses the single-directory layout; use the legacy root-level paths only for projects that `auto-iter doctor` reports as `layout: legacy`.
- If `raw_input/` conflicts with tracking information, treat tracking information as newer unless the user explicitly asks to verify against the original input.
- Any useful information found in `raw_input/` must be written back into tracking information so future sessions do not need to rediscover it.

## Experiment Protocol

- Every experiment must have one `run_id`.
- Every experiment must save resolved config, metrics, logs, and artifacts.
- Every conclusion must become a decision record with evidence run IDs.
- A rejected experiment from an external session still needs a `run_id`: use `auto-iter run import --config <file> --dataset <name> --status failed --summary "<why rejected>" --command "<external command or session>"`, then use that `run_id` as evidence for `decision add --status rejected`.
- For rejected parameter ranges, use `decision add --route-relation parameter-space --route-param name:min:max`.
- `run exec` writes run state to the resolved AIT project root, then launches its command from `--workdir`, `AUTO_ITER_WORKDIR`, or the current shell directory. The run summary records the shared AIT project root, workdir, Git branch, Git commit, and uncommitted change count from that workdir. Use `cd path/to/workdir && ...` inside `--command` only as a compatibility fallback for older installed AIT versions that do not support `--workdir`.
- Raw logs stay under `.auto_iter/runs/<run_id>/logs/` in the single-directory layout; do not paste full logs into context by default.
- Read summaries, metrics, artifacts, and decisions first; read raw logs only for a specific failure investigation.
- At session end, generate a handoff with:

```bash
auto-iter handoff generate
auto-iter handoff validate
```

- `auto-iter handoff generate` must be silent by default so Codex does not parse ordinary stdout as hook JSON. Use `auto-iter handoff generate --print-path` only for manual debugging. Do not use shell redirection or platform-specific null devices for this; the hook must work on Windows, WSL/Linux, and macOS.

## State Ownership

- SQLite database `.auto_iter/state/agent_state.db` is the factual source for runs, metrics, artifacts, decisions, route checks, and handoff records in the single-directory layout.
- Markdown files under `.auto_iter/decisions/` and `.auto_iter/handoffs/` are readable projections for humans and Codex. A decision projection is valid current context only if the matching record still exists in SQLite with the same status.
- Markdown files under `.auto_iter/topics/` are readable topic projections; `.auto_iter/topics/active_topic.md` is the default-topic compatibility projection, and `.auto_iter/topics/archive/` is loaded only on user request or confirmed topic switch.
- Markdown files under `.auto_iter/rules/` are readable rule projections; `.auto_iter/rules/current_effective.md` is the current effective rule snapshot, while SQLite remains the fact source for rule metadata and supersede chains.
- Topic evidence links live in SQLite and connect a topic to related run、decision、artifact records; Markdown topic projections and handoff only summarize those links.
- Markdown files under `.auto_iter/plans/` track managed-project implementation work and current engineering direction. In the AIT source repository, root-level `plans/` continues to track AIT tool implementation work until that repository is migrated.
- Demo or test histories may live under `examples/` when they document the test purpose and data boundary. Their sample IDs or parameters are not current project conclusions unless the current SQLite state contains matching records.
- `AGENTS.md` stores stable process rules only. Do not put changing experiment history here.
- In a target project, project-root `AGENTS.md` is optional. AIT includes it in generated handoff read order only when the file already exists; do not create it merely to satisfy AIT initialization.
