# AIT Worktree Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AIT keep one shared project state root while each Codex window and each run can use its own Git worktree execution directory.

**Architecture:** Add an explicit AIT project root override and an explicit run workdir. The project root controls where `.auto_iter` state is read and written; the workdir controls where experiment commands run and where Git branch/commit/dirty state is captured.

**Tech Stack:** Python standard library (`argparse`, `pathlib`, `sqlite3`, `subprocess`), existing `unittest` test suite, existing Markdown docs and skills.

---

## Terms

- AIT project root: the directory whose `.auto_iter/` holds state, runs, decisions, handoffs, topics, and search index.
- Workdir: the concrete filesystem directory where an experiment command runs, usually one Git worktree.
- Window default workdir: an environment variable value set per Codex window so different windows can run in different worktrees while sharing one AIT project root.

## File Structure

- Modify `auto_iteration/cli.py`
  - Add project-root override resolution.
  - Add workdir resolution.
  - Add run schema columns and migration.
  - Record workdir, project root, Git branch, Git commit, and dirty status from the workdir.
  - Run `run exec` commands from the resolved workdir.
  - Surface workdir in doctor, run summary, handoff, and search through existing Markdown projections.
- Modify `tests/test_cli.py`
  - Add regression tests for project-root override.
  - Add regression tests for per-window `AUTO_ITER_WORKDIR`.
  - Add regression tests for `run exec --workdir`.
  - Add regression tests that two workdirs write to one shared AIT state database.
- Modify `README.md`, `AGENTS.md`, `skills/auto-iteration-entry/SKILL.md`, and `skills/auto-iteration/SKILL.md`
  - Replace the current "put `cd <workdir>` inside `--command`" workaround with explicit project-root and workdir guidance.
  - Document multi-window usage.
- Modify `plans/global_plan.md`, `plans/version_iterations.md`, and `plans/active_plan.md`
  - Add the new version entry and mark this as the next AIT tool capability.

## Task 1: Add Explicit Project Root Resolution

**Files:**
- Modify: `auto_iteration/cli.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing test for environment project root**

Add a test that initializes AIT in one directory, runs `doctor` from a sibling directory with `AUTO_ITER_PROJECT_ROOT` set, and expects the initialized root to be used.

```python
def test_auto_iter_project_root_env_overrides_cwd(self):
    run_cli(self.tmp, "init")
    sibling = self.tmp.parent / f"{self.tmp.name}_sibling"
    sibling.mkdir()

    doctor = run_cli(
        sibling,
        "doctor",
        env_extra={"AUTO_ITER_PROJECT_ROOT": str(self.tmp)},
    )

    self.assertIn(f"root: {self.tmp}", doctor.stdout)
    self.assertIn(f"state_dir: {self.tmp / '.auto_iter'}", doctor.stdout)
```

- [x] **Step 2: Write failing test for command-line project root**

Add a test that passes `--project-root <path>` before the subcommand and expects it to override the current directory.

```python
def test_project_root_cli_arg_overrides_cwd(self):
    run_cli(self.tmp, "init")
    sibling = self.tmp.parent / f"{self.tmp.name}_project_root_cli"
    sibling.mkdir()

    doctor = run_cli(sibling, "--project-root", str(self.tmp), "doctor")

    self.assertIn(f"root: {self.tmp}", doctor.stdout)
    self.assertIn(f"state_dir: {self.tmp / '.auto_iter'}", doctor.stdout)
```

- [x] **Step 3: Run the focused tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests.test_auto_iter_project_root_env_overrides_cwd tests.test_cli.CliTests.test_project_root_cli_arg_overrides_cwd -v
```

Expected before implementation: both tests fail because `root()` still resolves from the current directory only.

- [x] **Step 4: Implement project-root override**

In `auto_iteration/cli.py`:

```python
PROJECT_ROOT_OVERRIDE: Path | None = None
PROJECT_ROOT_ENV_VAR = "AUTO_ITER_PROJECT_ROOT"
WORKDIR_ENV_VAR = "AUTO_ITER_WORKDIR"


def configured_project_root() -> Path | None:
    if PROJECT_ROOT_OVERRIDE is not None:
        return PROJECT_ROOT_OVERRIDE
    raw = os.environ.get(PROJECT_ROOT_ENV_VAR)
    if not raw:
        return None
    return Path(raw).expanduser().resolve()
```

Update `root()` so it first uses `configured_project_root()` when present. If the override path exists, return it. If it does not exist, raise `UserError("project root does not exist: <path>")`.

Update `build_parser()`:

```python
parser.add_argument("--project-root", help="AIT project root whose .auto_iter state should be used")
```

Update `main()` before `args.func(args)`:

```python
global PROJECT_ROOT_OVERRIDE
if getattr(args, "project_root", None):
    PROJECT_ROOT_OVERRIDE = Path(args.project_root).expanduser().resolve()
```

- [x] **Step 5: Verify focused tests pass**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests.test_auto_iter_project_root_env_overrides_cwd tests.test_cli.CliTests.test_project_root_cli_arg_overrides_cwd -v
```

Expected after implementation: both tests pass.

## Task 2: Add Workdir Resolution For Runs

**Files:**
- Modify: `auto_iteration/cli.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing test for `run exec --workdir`**

Create two directories under the same temp project. The command writes `pwd` to an artifact file. The run must execute from `--workdir`, but write state under the shared AIT root.

```python
def test_run_exec_uses_explicit_workdir_and_shared_state(self):
    run_cli(self.tmp, "init")
    workdir = self.tmp / "worktrees" / "exp-a"
    workdir.mkdir(parents=True)
    config = self.tmp / "config.json"
    config.write_text('{"route": "workdir-explicit"}\n', encoding="utf-8")
    output = workdir / "pwd.txt"

    result = run_cli(
        self.tmp,
        "run",
        "exec",
        "--workdir",
        str(workdir),
        "--config",
        str(config),
        "--dataset",
        "workdir-explicit",
        "--command",
        "pwd > pwd.txt",
        "--artifact",
        str(output),
    )

    self.assertIn("status=success", result.stdout)
    self.assertEqual(output.read_text(encoding="utf-8").strip(), str(workdir))
    run_id = result.stdout.split()[2]
    summary = (self.tmp / ".auto_iter" / "runs" / run_id / "summary.md").read_text(encoding="utf-8")
    self.assertIn(f"workdir: {workdir}", summary)
```

- [x] **Step 2: Write failing test for `AUTO_ITER_WORKDIR`**

```python
def test_run_exec_uses_auto_iter_workdir_env(self):
    run_cli(self.tmp, "init")
    workdir = self.tmp / "worktrees" / "exp-env"
    workdir.mkdir(parents=True)
    config = self.tmp / "config.json"
    config.write_text('{"route": "workdir-env"}\n', encoding="utf-8")
    output = workdir / "pwd-env.txt"

    result = run_cli(
        self.tmp,
        "run",
        "exec",
        "--config",
        str(config),
        "--dataset",
        "workdir-env",
        "--command",
        "pwd > pwd-env.txt",
        "--artifact",
        str(output),
        env_extra={"AUTO_ITER_WORKDIR": str(workdir)},
    )

    self.assertIn("status=success", result.stdout)
    self.assertEqual(output.read_text(encoding="utf-8").strip(), str(workdir))
```

- [x] **Step 3: Implement workdir helpers**

In `auto_iteration/cli.py`:

```python
def resolve_workdir(raw_workdir: str | None = None) -> Path:
    raw = raw_workdir or os.environ.get(WORKDIR_ENV_VAR)
    if raw:
        path = Path(raw).expanduser().resolve()
    else:
        path = Path.cwd().resolve()
    if not path.exists():
        raise UserError(f"workdir does not exist: {path}")
    if not path.is_dir():
        raise UserError(f"workdir is not a directory: {path}")
    return path
```

Add `--workdir` to `run start`, `run import`, and `run exec`.

- [x] **Step 4: Make `run exec` execute from the workdir**

Update `command_run_exec()`:

```python
workdir = resolve_workdir(args.workdir)
run_id = create_run_record(db, config, args.dataset, args.command, args.seed, args.session, workdir=workdir)
result = subprocess.run(args.command, cwd=workdir, text=True, capture_output=True, shell=True)
```

For `run start` and `run import`, call `resolve_workdir(args.workdir)` and pass it into `create_run_record()`.

- [x] **Step 5: Verify focused workdir tests pass**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests.test_run_exec_uses_explicit_workdir_and_shared_state tests.test_cli.CliTests.test_run_exec_uses_auto_iter_workdir_env -v
```

Expected: both tests pass.

## Task 3: Store Workdir And Git State In Runs

**Files:**
- Modify: `auto_iteration/cli.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing test for Git state from workdir**

Use a temporary Git repository and an extra worktree. Initialize AIT in the parent project root, execute a run in the worktree, and assert the run summary records the worktree branch and commit.

```python
def test_run_records_git_state_from_workdir(self):
    repo = self.tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, text=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, text=True, capture_output=True)
    subprocess.run(["git", "branch", "exp"], cwd=repo, check=True)
    workdir = self.tmp / "worktrees" / "exp"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", str(workdir), "exp"], check=True, text=True, capture_output=True)

    run_cli(self.tmp, "init")
    config = self.tmp / "config.json"
    config.write_text('{"route": "git-workdir"}\n', encoding="utf-8")
    result = run_cli(
        self.tmp,
        "run",
        "exec",
        "--workdir",
        str(workdir),
        "--config",
        str(config),
        "--dataset",
        "git-workdir",
        "--command",
        "true",
    )

    run_id = result.stdout.split()[2]
    summary = (self.tmp / ".auto_iter" / "runs" / run_id / "summary.md").read_text(encoding="utf-8")
    head = subprocess.run(["git", "-C", str(workdir), "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    self.assertIn(f"git_commit: {head}", summary)
    self.assertIn("git_branch: exp", summary)
    self.assertIn(f"workdir: {workdir}", summary)
```

- [x] **Step 2: Add run columns and migration**

In `init_schema()`, add these columns to new `runs` tables:

```sql
project_root text not null default '',
workdir text not null default '',
git_dirty_count integer not null default 0,
git_status_short text not null default ''
```

For existing databases, use the local schema migration pattern already present in `init_schema()`: inspect `pragma table_info(runs)` and `alter table runs add column ...` for missing columns.

- [x] **Step 3: Make Git helpers accept a directory**

Replace fixed-root Git helpers with directory-aware helpers:

```python
def git_value(args: list[str], cwd: Path | None = None) -> str:
    ...
    cwd=cwd or root()


def git_commit(cwd: Path | None = None) -> str:
    return git_value(["rev-parse", "HEAD"], cwd=cwd)


def git_branch(cwd: Path | None = None) -> str:
    return git_value(["branch", "--show-current"], cwd=cwd)


def git_status_short(cwd: Path | None = None) -> str:
    return git_value(["status", "--short"], cwd=cwd)
```

Define dirty count as the number of non-empty lines in `git_status_short(workdir)`.

- [x] **Step 4: Persist run context**

Update `create_run_record()` signature:

```python
def create_run_record(..., workdir: Path | None = None) -> str:
    resolved_workdir = workdir or resolve_workdir(None)
```

Insert `project_root`, `workdir`, `git_commit(resolved_workdir)`, `git_branch(resolved_workdir)`, `git_dirty_count`, and `git_status_short`.

- [x] **Step 5: Show run context in summaries and `run show`**

Update `write_run_summary()` so the top section includes:

```text
- project_root: <path>
- workdir: <path>
- git_dirty_count: <integer>
```

`run show` already dumps database rows as JSON, so it will expose new columns automatically.

- [x] **Step 6: Verify Git-state test passes**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests.test_run_records_git_state_from_workdir -v
```

Expected: the summary records the workdir branch and commit, not the AIT project root branch.

## Task 4: Surface Multi-Window Context In Doctor And Handoff

**Files:**
- Modify: `auto_iteration/cli.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Add doctor output test**

```python
def test_doctor_prints_project_root_and_workdir(self):
    run_cli(self.tmp, "init")
    workdir = self.tmp / "worktrees" / "exp-doctor"
    workdir.mkdir(parents=True)

    doctor = run_cli(
        self.tmp,
        "doctor",
        env_extra={"AUTO_ITER_WORKDIR": str(workdir)},
    )

    self.assertIn(f"root: {self.tmp}", doctor.stdout)
    self.assertIn(f"state_dir: {self.tmp / '.auto_iter'}", doctor.stdout)
    self.assertIn(f"workdir: {workdir}", doctor.stdout)
```

- [x] **Step 2: Add handoff output test**

Generate handoff with `AUTO_ITER_WORKDIR` and assert `Current Snapshot` includes `workdir`.

```python
def test_handoff_snapshot_includes_workdir(self):
    run_cli(self.tmp, "init")
    workdir = self.tmp / "worktrees" / "handoff-workdir"
    workdir.mkdir(parents=True)

    run_cli(self.tmp, "handoff", "generate", env_extra={"AUTO_ITER_WORKDIR": str(workdir)})
    text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")

    self.assertIn(f"- root: {self.tmp}", text)
    self.assertIn(f"- workdir: {workdir}", text)
```

- [x] **Step 3: Implement doctor and handoff display**

Update `command_doctor()` to print:

```text
root: <AIT project root>
state_dir: <AIT state dir>
workdir: <resolved workdir>
workdir_source: cli|env|cwd
```

For this task, `workdir_source` can be returned from `resolve_workdir_with_source()`:

```python
def resolve_workdir_with_source(raw_workdir: str | None = None) -> tuple[Path, str]:
    if raw_workdir:
        return resolve_workdir(raw_workdir), "cli"
    if os.environ.get(WORKDIR_ENV_VAR):
        return resolve_workdir(None), "env"
    return resolve_workdir(None), "cwd"
```

Update `build_handoff()` and `build_topic_handoff()` current snapshot sections to include `workdir`.

- [x] **Step 4: Verify doctor and handoff tests pass**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests.test_doctor_prints_project_root_and_workdir tests.test_cli.CliTests.test_handoff_snapshot_includes_workdir -v
```

Expected: both pass.

## Task 5: Update Documentation And Skills

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `skills/auto-iteration-entry/SKILL.md`
- Modify: `skills/auto-iteration/SKILL.md`
- Modify: `plans/global_plan.md`
- Modify: `plans/version_iterations.md`
- Modify: `plans/active_plan.md`
- Test: `tests/test_cli.py`

- [x] **Step 1: Add docs assertions**

Add tests that assert docs mention:

```text
AUTO_ITER_PROJECT_ROOT
AUTO_ITER_WORKDIR
--project-root
--workdir
```

Use existing docs tests near the current README, AGENTS, and skill assertions.

- [x] **Step 2: Update README usage**

Replace the old instruction that says `run exec` must use `cd path/to/workdir && ...` with:

```bash
AUTO_ITER_PROJECT_ROOT=/home/ryan/proj/valeo \
AUTO_ITER_WORKDIR=/home/ryan/proj/valeo/worktrees/<name> \
auto-iter run exec --config config.json --dataset dataset-id --command "<experiment command>"
```

Also document the explicit command form:

```bash
auto-iter --project-root /home/ryan/proj/valeo run exec \
  --workdir /home/ryan/proj/valeo/worktrees/<name> \
  --config config.json \
  --dataset dataset-id \
  --command "<experiment command>"
```

- [x] **Step 3: Update AGENTS and skills**

Add the rule:

```text
In multi-window work, keep one AUTO_ITER_PROJECT_ROOT per managed project and set AUTO_ITER_WORKDIR per Codex window. Use --workdir for any run whose execution directory differs from the current shell directory.
```

Replace old guidance that required embedding `cd` in `--command`. Keep a fallback note: if using an older installed AIT that lacks `--workdir`, use `cd <workdir> && ...` only as a compatibility workaround.

- [x] **Step 4: Update version tracking**

Set the next version in `plans/version_iterations.md`:

```text
- current_version: v0.42
- status: in_progress
- goal: 支持共享 AIT 项目根目录和每窗口独立 workdir，让 Git worktree 多窗口实验能写回同一状态库，并记录每条 run 的实际执行目录。
```

Add a `v0.42` task checklist covering project root, workdir, run context persistence, doctor/handoff display, docs, and tests.

Update `plans/global_plan.md` with a new capability section for Git worktree and multi-window execution context.

- [x] **Step 5: Verify docs tests pass**

Run:

```bash
python3 -m unittest tests.test_cli.CliTests -v
```

Expected: all docs-related and CLI tests pass.

## Task 6: Full Verification And Final Commit

**Files:**
- Verify all modified files.

- [x] **Step 1: Run full unit test suite**

Run:

```bash
python3 -Wd -m unittest discover -s tests -v
```

Expected: all tests pass.

- [x] **Step 2: Run syntax check**

Run:

```bash
python3 -m py_compile auto_iteration/cli.py
```

Expected: no output and exit code 0.

- [x] **Step 3: Run AIT doctor**

Run:

```bash
python3 -m auto_iteration.cli doctor
```

Expected: output includes `state: ok`, `database: ok`, `root: /home/ryan/auto_iteration`, and a `workdir:` line.

- [x] **Step 4: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [x] **Step 5: Review final diff**

Run:

```bash
git diff -- auto_iteration/cli.py tests/test_cli.py README.md AGENTS.md skills/auto-iteration-entry/SKILL.md skills/auto-iteration/SKILL.md plans/global_plan.md plans/version_iterations.md plans/active_plan.md
```

Expected: only the planned project-root/workdir changes appear.

- [x] **Step 6: Commit**

Run:

```bash
git add auto_iteration/cli.py tests/test_cli.py README.md AGENTS.md skills/auto-iteration-entry/SKILL.md skills/auto-iteration/SKILL.md plans/global_plan.md plans/version_iterations.md plans/active_plan.md
git commit -m "feat: support worktree execution context"
```

Expected: commit succeeds.

## Acceptance Criteria

- `auto-iter --project-root <root> doctor` uses `<root>/.auto_iter` regardless of current shell directory.
- `AUTO_ITER_PROJECT_ROOT=<root> auto-iter doctor` uses `<root>/.auto_iter`.
- `auto-iter run exec --workdir <worktree> ...` runs the command from `<worktree>`.
- `AUTO_ITER_WORKDIR=<worktree> auto-iter run exec ...` uses `<worktree>` when `--workdir` is absent.
- Two Codex windows can use the same `AUTO_ITER_PROJECT_ROOT` with different `AUTO_ITER_WORKDIR` values.
- Each run summary shows project root, workdir, Git branch, Git commit, and dirty count from the workdir.
- Handoff and doctor show the resolved workdir.
- Existing projects continue to work without setting any new environment variable.
