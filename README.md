# auto_iteration

`auto_iteration` is a local state manager for long-running Codex-assisted algorithm experiments.

The goal is to stop treating chat history as project state. Experiment facts go into SQLite, readable summaries go into Markdown, and fresh Codex sessions resume from a generated handoff.

## Minimum Workflow

Initialize a project:

```bash
python3 -m auto_iteration.cli init
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

## Storage Rule

- `state/agent_state.db`: factual source for runs, metrics, artifacts, decisions, route checks, and handoffs.
- `decisions/`: readable decision projections.
- `handoffs/latest_handoff.md`: fresh-session entry point.
- `runs/<run_id>/`: per-run config snapshot and future logs/artifacts.

