# auto_iteration

`auto_iteration` is a local state manager for long-running Codex-assisted algorithm experiments.

The goal is to stop treating chat history as project state. Experiment facts go into SQLite, readable summaries go into Markdown, and fresh Codex sessions resume from a generated handoff.

## Minimum Workflow

Use inside this repository:

```bash
python3 -m auto_iteration.cli init
```

Use from another algorithm repository by running the wrapper with an absolute path. The wrapper keeps the tool code in `/home/ryan/auto_iteration`, while the current working directory becomes the project whose experiments are recorded:

```bash
cd /path/to/algorithm_repo
python3 /home/ryan/auto_iteration/tools/auto_iter.py init
```

For convenience, create a shell alias named `auto-iter` (only a shorter command name):

```bash
alias auto-iter='python3 /home/ryan/auto_iteration/tools/auto_iter.py'
```

Then run commands from the target project root:

```bash
auto-iter doctor
```

Check state:

```bash
python3 -m auto_iteration.cli doctor
```

Record a run:

```bash
python3 -m auto_iteration.cli run start --config config.json --dataset demo --command "python experiment.py"
python3 -m auto_iteration.cli run finish <run_id> --status success --metrics metrics.json --artifact report.md
```

Block repeated failed routes:

```bash
python3 -m auto_iteration.cli decision add --status rejected --evidence <run_id> --title "<中文标题>" --claim "<中文结论>" --route-keyword "<关键词>"
python3 -m auto_iteration.cli route check --config config.json --summary "<中文路线说明>"
```

Generate handoff:

```bash
python3 -m auto_iteration.cli handoff generate
python3 -m auto_iteration.cli resume
```

When using the `auto-iter` alias in another repository, replace `python3 -m auto_iteration.cli` with `auto-iter`.

## Version Task Tracking

Use `plans/version_iterations.md` as the version-level task tracker. It records each version's goal, task checklist, acceptance checks, evidence, and next-version direction.

Before changing implementation scope, update:

```bash
sed -n '1,220p' plans/version_iterations.md
sed -n '1,160p' plans/active_plan.md
```

At session end, regenerate the handoff so the next Codex session sees the current version state:

```bash
python3 -m auto_iteration.cli handoff generate
```

## Storage Rule

- `state/agent_state.db`: factual source for runs, metrics, artifacts, decisions, route checks, and handoffs.
- `decisions/`: readable decision projections.
- `handoffs/latest_handoff.md`: fresh-session entry point.
- `plans/version_iterations.md`: version-level task tracker.
- `plans/active_plan.md`: current engineering direction.
- `runs/<run_id>/`: per-run config snapshot and future logs/artifacts.
