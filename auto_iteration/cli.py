from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path("state") / "agent_state.db"
TOOL_ROOT = Path(__file__).resolve().parents[1]
DECISION_STATUSES = {"active", "rejected", "superseded", "open"}
RUN_STATUSES = {"running", "success", "failed", "aborted"}
ACTIVE_PLAN_TEMPLATE = """# Active Plan

## 当前目标

- 建立 Codex 长周期算法迭代的本地状态闭环。

## 当前版本

- 读取 `plans/global_plan.md` 和 `plans/version_iterations.md`，按当前版本的任务清单推进。

## 下一步

1. 设计 handoff 完整性校验的最小字段集合。
2. 设计路线关系增强的最小数据结构。
3. 每次版本范围变化时，先更新 `plans/version_iterations.md`。
4. 会话结束前运行 `handoff generate`。
"""

VERSION_ITERATIONS_TEMPLATE = """# Version Iteration Tracking

## 说明

这个文件记录每次版本迭代的目标、任务状态、验收证据、后续方向，以及当前版本整体距离 `global plan` 的差距。`global plan` 的定义和完整清单在 `plans/global_plan.md`。

- `pending` 表示还没开始。
- `in_progress` 表示正在做。
- `done` 表示已经完成并有证据。
- `blocked` 表示被外部条件卡住。
- `deferred` 表示明确放到后续版本。

## 全局方案方向

- 详见 `plans/global_plan.md`。

## 当前版本

- current_version: v0.2
- status: done
- goal: 让 Codex agent 在 Codex CLI 会话内自动调用 `auto-iter`，用户不需要退出 Codex 或手写绝对路径。

## v0.1 任务清单

- [x] 初始化目录：`state/`、`runs/`、`handoffs/`、`decisions/`、`plans/`。
- [x] 初始化 SQLite 数据库：记录 runs、metrics、artifacts、decisions、handoffs、route_checks。
- [x] 记录实验开始：`run start` 写入配置、数据集、命令、Git commit 和 Git branch。
- [x] 记录实验结束：`run finish` 写入状态、指标和工件路径。
- [x] 查询实验：`run list` 和 `run show`。
- [x] 记录结论：`decision add` 写入 active、rejected、superseded、open 状态。
- [x] 替代旧结论：`decision supersede` 把旧结论移动到 superseded。
- [x] 阻断重复路线：`route check` 检查重复配置以及 rejected/superseded 关键词。
- [x] 生成交接：`handoff generate` 生成 `handoffs/latest_handoff.md`。
- [x] 恢复交接：`resume` 输出下一轮应该先读的 handoff。
- [x] Codex Stop hook：`.codex/hooks.json` 调用 handoff 生成命令。
- [x] Codex skill：`skills/auto-iteration/SKILL.md` 记录使用流程。
- [x] 十轮 demo：验证从多轮实验到结论沉淀的闭环。
- [x] 版本任务跟踪：每个版本都有任务状态、验收证据和下一步方向。
- [x] handoff 接入版本任务跟踪：新 session 能看到当前版本和下一步工程任务。
- [x] 结束汇报规则：每次任务结束前报告当前版本号、本次完成项、当前版本内部剩余项、当前版本整体距离 `global plan` 的差距。
- [x] 日志摘要：自动生成 `runs/<run_id>/summary.md` 和 `runs/<run_id>/logs/error_summary.md`。
- [x] 实验命令封装：自动执行命令并捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。

## v0.1 距离 global plan

v0.1 的定位是打底版本：先让实验事实、结论、计划和 handoff 有固定落点。它不是完整的 `global plan`。

v0.1 已覆盖的全局能力：

- 账本层基础：SQLite 已记录 run、metric、artifact、decision、handoff、route check。
- 叙事层基础：`decisions/`、`handoffs/`、`plans/` 已有固定入口。
- 流程层基础：`AGENTS.md`、skill、Stop hook 已有固定规则。
- 重复路线拦截基础：能按配置哈希和 rejected/superseded 关键词阻断明显重复路线。
- 日志分级基础：每个 run 已有 `summary.md` 和 `logs/error_summary.md`，原始 stdout/stderr/debug 日志保留在 `logs/` 下。
- 实验执行基础：`run exec` 能执行单条实验命令并自动写入状态库和日志文件。

v0.1 之后仍未覆盖的全局能力：

- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 可选的语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## v0.1 验收标准

1. `python3 -m auto_iteration.cli doctor` 通过。
2. `python3 -Wd -m unittest discover -s tests -v` 通过。
3. `handoffs/latest_handoff.md` 包含版本任务跟踪文件路径。
4. `plans/version_iterations.md` 明确列出当前版本状态、已完成任务、未完成任务和后续版本方向。

## v0.2 任务清单

- [x] 提供可安装的短命令入口 `auto-iter`。
- [x] 新增 Codex 入口 skill：`skills/auto-iteration-entry/SKILL.md`。
- [x] 入口 skill 指导 agent 在任务开始、实验前、实验后、任务结束时自动调用 `auto-iter`。
- [x] 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- [x] 提供端到端演示：测试覆盖 doctor、resume、route check、run exec、decision add、handoff generate。

## v0.2 距离 global plan

v0.2 覆盖了 Codex 入口能力：用户可以在 Codex CLI 内表达任务，agent 通过入口 skill 在同一会话内调用 `auto-iter`。

v0.2 已覆盖的全局能力：

- Codex 入口 skill：`auto-iteration-entry`。
- 短命令入口：`auto-iter`。
- 入口流程：doctor、resume、route check、run exec、decision add、handoff generate。
- 端到端演示：临时项目中通过已安装 `auto-iter` 完成完整流程。

v0.2 之后仍未覆盖的全局能力：

- handoff 完整性校验，检查关键字段缺失。
- 更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。
- 按标题索引动态载入上下文，避免一次性塞入所有历史。
- 可选语义检索：当 decision、handoff、retrospective 数量变多后再加入。

## 后续版本方向

### v0.2

- done：Codex 入口能力已完成。

### v0.3

- 增加 handoff 完整性校验，检查关键字段是否缺失。
- 增加更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。

### v0.4

- 增加按标题索引读取的上下文机制：先读目录和摘要，需要时再读详细记录。
- 增加任务状态命令，减少手工维护 Markdown 的出错概率。
- 在 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
"""

GLOBAL_PLAN_TEMPLATE = """# Global Plan

## 定义

`global plan` 指整个长周期算法迭代上下文管理方案。它不是某一个版本，也不是单个 skill；它的目标是让 Codex agent 在长周期实验中能恢复状态、避免重复路线、保存证据、生成交接，并在 Codex CLI 会话内主动调用本地工具。

## 总体形态

最终形态是轻量本地编排系统加 Codex 入口能力。

- 轻量本地编排系统：`auto_iteration` 负责写 SQLite、记录 runs、记录 decisions、保存 logs、生成 summaries、生成 handoff。
- Codex 入口能力：Codex agent 在会话内知道何时调用 `auto-iter`，用户不需要退出 Codex CLI，也不需要每次手写绝对路径。

## 全局能力清单

### 1. 状态账本

- 记录 run、config、dataset、command、git commit、git branch。
- 记录 metrics 和 artifacts。
- 记录 run 状态：running、success、failed、aborted。
- 每个实验都有 `run_id`。

### 2. 日志和摘要

- 捕获 `stdout.log`、`stderr.log`、`debug.jsonl`。
- 生成 `summary.md`。
- 生成 `logs/error_summary.md`。
- 默认读取 summary 和 error_summary；只有调查具体失败时才读原始日志。

### 3. 结论和路线控制

- 记录 active、rejected、superseded、open 状态的 decision。
- 每个 decision 必须有 evidence run IDs。
- 新路线前运行 route check。
- 阻止明显重复配置和 rejected/superseded 路线。
- 后续增强方法被替代、参数空间被部分否定、重开条件提示。

### 4. 交接和恢复

- 自动生成 `handoffs/latest_handoff.md`。
- handoff 指向 run summaries、decisions、plans，而不是粘贴完整原始日志。
- 新 Codex session 先读 `AGENTS.md`、handoff、global plan、version tracking、active plan。
- 后续增加 handoff 完整性校验，检查关键字段缺失。

### 5. Codex 入口能力

- 提供 Codex 入口 skill：告诉 agent 什么时候调用 `auto-iter doctor`、`auto-iter resume`、`auto-iter route check`、`auto-iter run exec`、`auto-iter decision add`、`auto-iter handoff generate`。
- 提供短命令入口 `auto-iter`，避免每次写 `python3 /home/ryan/auto_iteration/tools/auto_iter.py`。
- 用户在 Codex CLI 中表达任务，agent 在同一个会话里调用命令；用户不需要退出 Codex CLI。
- 入口 skill 只负责流程触发和命令调用顺序；状态写入仍由 `auto_iteration` 完成。

### 6. 动态载入上下文

- 建立按标题索引的上下文读取方式：先读目录和摘要，需要时再读详细内容。
- handoff、decision、run summary、error summary 都应可被按需读取。
- 避免一次性把所有历史塞进上下文。

### 7. 后续可选语义检索

- 当 decision、handoff、retrospective 数量变多后，再评估是否加入语义检索。
- 语义检索只能作为补充入口，不能替代 SQLite、plans 和 handoff 的明确证据链。

## 版本路线

### v0.1：本地状态闭环

状态：done。

范围：

- SQLite 状态库。
- run、metric、artifact、decision、handoff、route check。
- `run exec` 执行命令并捕获日志。
- run summary 和 error summary。
- version task tracking。

### v0.2：Codex 入口能力

状态：done。

目标：用户在 Codex CLI 内只表达任务，Codex agent 根据入口 skill 自动调用 `auto-iter`，不需要用户退出 Codex 或手写绝对路径。

任务：

- 提供可安装的短命令入口 `auto-iter`。
- 新增或调整 Codex 入口 skill，让 agent 在任务开始、实验前、实验后、任务结束时自动调用对应命令。
- 更新 `AGENTS.md`、README、handoff 读取顺序，让 `plans/global_plan.md` 成为固定读取对象。
- 提供一次端到端演示：从 Codex 会话内恢复状态、route check、run exec、decision add、handoff generate。

### v0.3：handoff 校验和路线关系增强

目标：减少交接字段缺失和重复路线误判。

任务：

- 增加 handoff 完整性校验。
- 增加更强的路线关系管理，例如方法被替代、参数空间被部分否定、重开条件自动提示。

### v0.4：动态载入上下文

目标：按标题索引和摘要读取历史，减少 token 占用。

任务：

- 建立 handoff、decision、run summary 的标题索引。
- 先读目录和摘要，需要时再读详细内容。
- 增加任务状态命令，减少手工维护 Markdown 的出错概率。
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def root() -> Path:
    return Path.cwd().resolve()


def db_path() -> Path:
    return root() / DB_PATH


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise UserError("state database does not exist; run `auto-iteration init` first")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def database(require_existing: bool = True) -> sqlite3.Connection:
    if require_existing:
        db = connect()
    else:
        db = sqlite3.connect(db_path())
        db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


class UserError(Exception):
    pass


def read_json(path: str | Path) -> Any:
    resolved = Path(path).expanduser().resolve()
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UserError(f"file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise UserError(f"invalid JSON in {resolved}: {exc}") from exc


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_data(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_dir(run_id: str) -> Path:
    return root() / "runs" / run_id


def logs_dir(run_id: str) -> Path:
    return run_dir(run_id) / "logs"


def git_value(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root(),
            text=True,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def git_commit() -> str:
    return git_value(["rev-parse", "HEAD"])


def git_branch() -> str:
    return git_value(["branch", "--show-current"])


def ensure_dirs() -> None:
    for path in [
        "state",
        "runs",
        "handoffs/archive",
        "decisions/active",
        "decisions/rejected",
        "decisions/superseded",
        "decisions/open",
        "plans",
    ]:
        (root() / path).mkdir(parents=True, exist_ok=True)


def write_if_missing(path: Path, text: str) -> None:
    if not path.exists():
        path.write_text(text.rstrip() + "\n", encoding="utf-8")


def ensure_plan_files() -> None:
    write_if_missing(root() / "plans" / "global_plan.md", GLOBAL_PLAN_TEMPLATE)
    write_if_missing(root() / "plans" / "active_plan.md", ACTIVE_PLAN_TEMPLATE)
    write_if_missing(root() / "plans" / "version_iterations.md", VERSION_ITERATIONS_TEMPLATE)


def init_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        create table if not exists projects (
            project_id text primary key,
            root_path text not null,
            current_goal text not null default ''
        );

        create table if not exists runs (
            run_id text primary key,
            project_id text not null,
            session_id text,
            git_commit text not null,
            git_branch text not null,
            dataset_id text not null,
            seed text,
            command text not null,
            config_json text not null,
            config_hash text not null,
            status text not null,
            started_at text not null,
            ended_at text,
            summary text not null default ''
        );

        create table if not exists metrics (
            run_id text not null,
            metric_name text not null,
            metric_value real not null,
            unit text not null,
            direction text not null,
            primary key (run_id, metric_name)
        );

        create table if not exists artifacts (
            artifact_id text primary key,
            run_id text not null,
            kind text not null,
            path text not null,
            sha256 text not null,
            summary text not null default ''
        );

        create table if not exists decisions (
            decision_id text primary key,
            status text not null,
            title text not null,
            claim text not null,
            evidence_run_ids_json text not null,
            route_keywords_json text not null,
            supersedes_decision_id text,
            reopen_condition text not null default '',
            created_at text not null
        );

        create table if not exists handoffs (
            handoff_id text primary key,
            created_at text not null,
            based_on_run_id text,
            path text not null,
            handoff_md text not null
        );

        create table if not exists route_checks (
            check_id text primary key,
            created_at text not null,
            proposed_config_hash text not null,
            proposed_summary text not null,
            result text not null,
            matched_decision_ids_json text not null
        );
        """
    )


def command_init(_args: argparse.Namespace) -> int:
    ensure_dirs()
    ensure_plan_files()
    with database(require_existing=False) as db:
        init_schema(db)
        project_id = hashlib.sha256(str(root()).encode("utf-8")).hexdigest()[:12]
        db.execute(
            """
            insert into projects (project_id, root_path, current_goal)
            values (?, ?, '')
            on conflict(project_id) do update set root_path = excluded.root_path
            """,
            (project_id, str(root())),
        )
    print(f"initialized {root()}")
    return 0


def command_doctor(_args: argparse.Namespace) -> int:
    missing = [name for name in ["state", "runs", "handoffs", "decisions", "plans"] if not (root() / name).exists()]
    if missing:
        raise UserError("missing directories: " + ", ".join(missing))
    missing_files = [
        name
        for name in ["plans/global_plan.md", "plans/active_plan.md", "plans/version_iterations.md"]
        if not (root() / name).exists()
    ]
    if missing_files:
        raise UserError("missing plan files: " + ", ".join(missing_files))
    print("state: ok")
    with database() as db:
        row = db.execute("select count(*) from sqlite_master where type = 'table'").fetchone()
    if row[0] < 7:
        raise UserError("database schema is incomplete")
    print("database: ok")
    print(f"root: {root()}")
    return 0


def default_bin_dir() -> Path:
    return Path.home() / ".local" / "bin"


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def command_install(args: argparse.Namespace) -> int:
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    skills_dir = Path(args.skills_dir).expanduser().resolve()
    bin_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    command_path = bin_dir / "auto-iter"
    tool_path = TOOL_ROOT / "tools" / "auto_iter.py"
    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f'exec python3 "{tool_path}" "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    command_path.chmod(0o755)

    source_skill = TOOL_ROOT / "skills" / "auto-iteration-entry"
    if not source_skill.exists():
        raise UserError(f"entry skill source does not exist: {source_skill}")
    target_skill = skills_dir / "auto-iteration-entry"
    shutil.copytree(source_skill, target_skill, dirs_exist_ok=True)

    print(f"installed command: {command_path}")
    print(f"installed skill: {target_skill}")
    return 0


def new_id(prefix: str) -> str:
    value = hashlib.sha256(f"{prefix}:{now_iso()}:{os.getpid()}:{root()}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{value}"


def command_run_start(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    with database() as db:
        run_id = create_run_record(db, config, args.dataset, args.command, args.seed, args.session)
    print(f"started run {run_id}")
    return 0


def create_run_record(
    db: sqlite3.Connection,
    config: Any,
    dataset: str,
    command: str,
    seed: str | None = None,
    session: str | None = None,
) -> str:
    run_id = new_id("R")
    current_run_dir = run_dir(run_id)
    logs_dir(run_id).mkdir(parents=True, exist_ok=True)
    (current_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    for log_name in ["stdout.log", "stderr.log", "debug.jsonl"]:
        (logs_dir(run_id) / log_name).touch()
    config_text = json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True)
    (current_run_dir / "config_resolved.json").write_text(config_text + "\n", encoding="utf-8")
    config_hash = hash_data(config)
    project = db.execute("select project_id from projects limit 1").fetchone()
    project_id = project["project_id"] if project else "default"
    db.execute(
        """
        insert into runs (
            run_id, project_id, session_id, git_commit, git_branch, dataset_id,
            seed, command, config_json, config_hash, status, started_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)
        """,
        (
            run_id,
            project_id,
            session,
            git_commit(),
            git_branch(),
            dataset,
            seed,
            command,
            stable_json(config),
            config_hash,
            now_iso(),
        ),
    )
    return run_id


def normalize_metric(value: Any) -> tuple[float, str, str]:
    if isinstance(value, dict):
        metric_value = float(value["value"])
        unit = str(value.get("unit", ""))
        direction = str(value.get("direction", ""))
        return metric_value, unit, direction
    return float(value), "", ""


def add_artifact(db: sqlite3.Connection, run_id: str, artifact_path: str, kind: str = "other") -> None:
    path = Path(artifact_path).expanduser().resolve()
    if not path.exists():
        raise UserError(f"artifact does not exist: {path}")
    artifact_id = "A-" + hashlib.sha256(f"{run_id}:{path}".encode("utf-8")).hexdigest()[:10]
    db.execute(
        """
        insert or replace into artifacts (artifact_id, run_id, kind, path, sha256, summary)
        values (?, ?, ?, ?, ?, ?)
        """,
        (artifact_id, run_id, kind, str(path), file_sha256(path), path.name),
    )


def summarize_text(text: str, max_lines: int = 40, max_chars: int = 4000) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = ["... truncated earlier lines ...", *lines[-max_lines:]]
    summarized = "\n".join(lines)
    if len(summarized) > max_chars:
        summarized = "... truncated earlier characters ...\n" + summarized[-max_chars:]
    return summarized


def write_debug_event(run_id: str, event: str, payload: dict[str, Any]) -> None:
    path = logs_dir(run_id) / "debug.jsonl"
    record = {"time": now_iso(), "event": event, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_error_summary(run_id: str, returncode: int | None = None) -> None:
    stderr_path = logs_dir(run_id) / "stderr.log"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    lines = [
        "# Error Summary",
        "",
        f"- run_id: {run_id}",
        f"- returncode: {returncode if returncode is not None else 'unknown'}",
        "",
        "## stderr",
    ]
    if stderr_text.strip():
        lines += ["", "```text", summarize_text(stderr_text), "```"]
    else:
        lines.append("No stderr output.")
    (logs_dir(run_id) / "error_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_summary(db: sqlite3.Connection, run_id: str) -> None:
    run = db.execute("select * from runs where run_id = ?", (run_id,)).fetchone()
    if not run:
        raise UserError(f"unknown run_id: {run_id}")
    metrics = db.execute("select * from metrics where run_id = ? order by metric_name", (run_id,)).fetchall()
    artifacts = db.execute("select * from artifacts where run_id = ? order by path", (run_id,)).fetchall()
    lines = [
        "# Run Summary",
        "",
        f"- run_id: {run['run_id']}",
        f"- status: {run['status']}",
        f"- dataset_id: {run['dataset_id']}",
        f"- git_commit: {run['git_commit']}",
        f"- git_branch: {run['git_branch']}",
        f"- config_hash: {run['config_hash']}",
        f"- command: {run['command']}",
        "",
        "## Metrics",
    ]
    if metrics:
        for row in metrics:
            unit = f" {row['unit']}" if row["unit"] else ""
            direction = f" direction={row['direction']}" if row["direction"] else ""
            lines.append(f"- {row['metric_name']}: {row['metric_value']}{unit}{direction}")
    else:
        lines.append("- none")
    lines += ["", "## Artifacts"]
    if artifacts:
        for row in artifacts:
            lines.append(f"- {row['kind']}: {row['path']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Logs",
        f"- stdout: {logs_dir(run_id) / 'stdout.log'}",
        f"- stderr: {logs_dir(run_id) / 'stderr.log'}",
        f"- debug: {logs_dir(run_id) / 'debug.jsonl'}",
        f"- error_summary: {logs_dir(run_id) / 'error_summary.md'}",
        "",
    ]
    (run_dir(run_id) / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def finish_run_record(
    db: sqlite3.Connection,
    run_id: str,
    status: str,
    metrics: dict[str, Any],
    artifact_paths: list[str],
    returncode: int | None = None,
) -> None:
    if status not in RUN_STATUSES:
        raise UserError(f"invalid status: {status}")
    existing = db.execute("select run_id from runs where run_id = ?", (run_id,)).fetchone()
    if not existing:
        raise UserError(f"unknown run_id: {run_id}")
    for name, raw_value in metrics.items():
        value, unit, direction = normalize_metric(raw_value)
        db.execute(
            """
            insert or replace into metrics (run_id, metric_name, metric_value, unit, direction)
            values (?, ?, ?, ?, ?)
            """,
            (run_id, name, value, unit, direction),
        )
    for path in artifact_paths:
        add_artifact(db, run_id, path)
    summary = f"status={status}; metrics={', '.join(sorted(metrics))}"
    db.execute(
        "update runs set status = ?, ended_at = ?, summary = ? where run_id = ?",
        (status, now_iso(), summary, run_id),
    )
    write_error_summary(run_id, returncode)
    write_run_summary(db, run_id)


def command_run_finish(args: argparse.Namespace) -> int:
    metrics = read_json(args.metrics) if args.metrics else {}
    with database() as db:
        finish_run_record(db, args.run_id, args.status, metrics, args.artifact)
    print(f"finished run {args.run_id}")
    return 0


def command_run_exec(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    with database() as db:
        run_id = create_run_record(db, config, args.dataset, args.command, args.seed, args.session)
        write_debug_event(run_id, "started", {"command": args.command})
        result = subprocess.run(args.command, cwd=root(), text=True, capture_output=True, shell=True)
        (logs_dir(run_id) / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (logs_dir(run_id) / "stderr.log").write_text(result.stderr, encoding="utf-8")
        status = "success" if result.returncode == 0 else "failed"
        write_debug_event(
            run_id,
            "finished",
            {"returncode": result.returncode, "status": status},
        )
        metrics = read_json(args.metrics) if args.metrics and Path(args.metrics).exists() else {}
        finish_run_record(db, run_id, status, metrics, args.artifact, result.returncode)
    print(f"executed run {run_id} status={status} returncode={result.returncode}")
    return result.returncode


def command_run_list(args: argparse.Namespace) -> int:
    with database() as db:
        rows = db.execute(
            """
            select run_id, status, dataset_id, started_at, ended_at
            from runs
            order by started_at desc
            limit ?
            """,
            (args.latest,),
        ).fetchall()
    for row in rows:
        print(f"{row['run_id']} {row['status']} dataset={row['dataset_id']} started={row['started_at']}")
    return 0


def command_run_show(args: argparse.Namespace) -> int:
    with database() as db:
        run = db.execute("select * from runs where run_id = ?", (args.run_id,)).fetchone()
        if not run:
            raise UserError(f"unknown run_id: {args.run_id}")
        metrics = db.execute("select * from metrics where run_id = ? order by metric_name", (args.run_id,)).fetchall()
        artifacts = db.execute("select * from artifacts where run_id = ? order by path", (args.run_id,)).fetchall()
    data = dict(run)
    data["config_json"] = json.loads(data["config_json"])
    data["metrics"] = [dict(row) for row in metrics]
    data["artifacts"] = [dict(row) for row in artifacts]
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def decision_path(status: str, decision_id: str) -> Path:
    return root() / "decisions" / status / f"{decision_id}.md"


def write_decision_projection(
    decision_id: str,
    status: str,
    title: str,
    claim: str,
    evidence: list[str],
    route_keywords: list[str],
    reopen_condition: str,
    supersedes: str | None,
) -> None:
    path = decision_path(status, decision_id)
    lines = [
        f"# {title}",
        "",
        f"- decision_id: {decision_id}",
        f"- status: {status}",
        f"- evidence_run_ids: {', '.join(evidence)}",
    ]
    if supersedes:
        lines.append(f"- supersedes_decision_id: {supersedes}")
    if route_keywords:
        lines.append(f"- route_keywords: {', '.join(route_keywords)}")
    if reopen_condition:
        lines.append(f"- reopen_condition: {reopen_condition}")
    lines += ["", "## 结论", claim, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def command_decision_add(args: argparse.Namespace) -> int:
    if args.status not in DECISION_STATUSES:
        raise UserError(f"invalid decision status: {args.status}")
    evidence = args.evidence or []
    if not evidence:
        raise UserError("at least one --evidence run_id is required")
    decision_id = new_id("D")
    route_keywords = args.route_keyword or []
    with database() as db:
        for run_id in evidence:
            if not db.execute("select run_id from runs where run_id = ?", (run_id,)).fetchone():
                raise UserError(f"unknown evidence run_id: {run_id}")
        db.execute(
            """
            insert into decisions (
                decision_id, status, title, claim, evidence_run_ids_json,
                route_keywords_json, supersedes_decision_id, reopen_condition, created_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                args.status,
                args.title,
                args.claim,
                json.dumps(evidence, ensure_ascii=False),
                json.dumps(route_keywords, ensure_ascii=False),
                args.supersedes,
                args.reopen_condition or "",
                now_iso(),
            ),
        )
    write_decision_projection(
        decision_id,
        args.status,
        args.title,
        args.claim,
        evidence,
        route_keywords,
        args.reopen_condition or "",
        args.supersedes,
    )
    print(f"added decision {decision_id}")
    return 0


def command_decision_supersede(args: argparse.Namespace) -> int:
    with database() as db:
        old = db.execute("select * from decisions where decision_id = ?", (args.old_id,)).fetchone()
        new = db.execute("select * from decisions where decision_id = ?", (args.new_id,)).fetchone()
        if not old:
            raise UserError(f"unknown old decision: {args.old_id}")
        if not new:
            raise UserError(f"unknown new decision: {args.new_id}")
        db.execute(
            "update decisions set status = 'superseded', supersedes_decision_id = ? where decision_id = ?",
            (args.new_id, args.old_id),
        )
    old_path = decision_path(old["status"], args.old_id)
    new_path = decision_path("superseded", args.old_id)
    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
    print(f"superseded decision {args.old_id} by {args.new_id}")
    return 0


def command_route_check(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    config_hash = hash_data(config)
    summary = args.summary
    matched: list[sqlite3.Row] = []
    reasons: list[str] = []
    with database() as db:
        exact = db.execute(
            "select run_id, status from runs where config_hash = ? order by started_at desc limit 1",
            (config_hash,),
        ).fetchone()
        if exact:
            reasons.append(f"same config already recorded by run {exact['run_id']} status={exact['status']}")
        decisions = db.execute(
            """
            select * from decisions
            where status in ('rejected', 'superseded')
            order by created_at desc
            """
        ).fetchall()
        for decision in decisions:
            keywords = json.loads(decision["route_keywords_json"])
            if keywords and all(keyword in summary or keyword in stable_json(config) for keyword in keywords):
                matched.append(decision)
        result = "block" if matched or exact else "allow"
        check_id = new_id("C")
        db.execute(
            """
            insert into route_checks (
                check_id, created_at, proposed_config_hash, proposed_summary, result, matched_decision_ids_json
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (check_id, now_iso(), config_hash, summary, result, json.dumps([row["decision_id"] for row in matched])),
        )
    if result == "allow":
        print("ALLOWED")
        print("No rejected or superseded route matched this proposal.")
        return 0
    print("BLOCKED")
    for reason in reasons:
        print(f"- {reason}")
    for decision in matched:
        evidence = ", ".join(json.loads(decision["evidence_run_ids_json"]))
        print(f"- {decision['decision_id']}: {decision['title']}")
        print(f"  evidence_run_ids: {evidence}")
        if decision["reopen_condition"]:
            print(f"  reopen_condition: {decision['reopen_condition']}")
    return 2


def latest_runs(db: sqlite3.Connection) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
    success = db.execute(
        "select * from runs where status = 'success' order by ended_at desc, rowid desc limit 1"
    ).fetchone()
    failed = db.execute(
        "select * from runs where status in ('failed', 'aborted') order by ended_at desc, rowid desc limit 1"
    ).fetchone()
    return success, failed


def artifact_lines(db: sqlite3.Connection, run_id: str) -> list[str]:
    rows = db.execute("select kind, path from artifacts where run_id = ? order by path", (run_id,)).fetchall()
    return [f"  - {row['kind']}: {row['path']}" for row in rows]


def build_handoff(db: sqlite3.Connection) -> tuple[str, str | None]:
    success, failed = latest_runs(db)
    active = db.execute("select * from decisions where status = 'active' order by created_at desc").fetchall()
    rejected = db.execute("select * from decisions where status = 'rejected' order by created_at desc").fetchall()
    open_items = db.execute("select * from decisions where status = 'open' order by created_at desc").fetchall()
    project = db.execute("select current_goal from projects limit 1").fetchone()
    current_goal = project["current_goal"] if project and project["current_goal"] else "未设置；请在下一轮实验前明确当前优化目标。"
    lines = [
        "# Latest Handoff",
        "",
        "## 当前目标",
        f"- {current_goal}",
        "",
        "## 当前快照",
        f"- root: {root()}",
        f"- branch: {git_branch()}",
        f"- commit: {git_commit()}",
        f"- latest_successful_run_id: {success['run_id'] if success else 'none'}",
        f"- latest_failed_run_id: {failed['run_id'] if failed else 'none'}",
        f"- global_plan: {root() / 'plans' / 'global_plan.md'}",
        f"- version_task_tracking: {root() / 'plans' / 'version_iterations.md'}",
        f"- active_plan: {root() / 'plans' / 'active_plan.md'}",
        "",
        "## 最近成功实验",
    ]
    if success:
        lines.append(f"- {success['run_id']}: dataset={success['dataset_id']} status={success['status']}")
        lines += artifact_lines(db, success["run_id"])
    else:
        lines.append("- none")
    lines += ["", "## 当前有效结论"]
    if active:
        for row in active:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            lines.append(f"  - {row['claim']}")
    else:
        lines.append("- none")
    lines += ["", "## 已废弃且不要重复的路线"]
    if rejected:
        for row in rejected:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            if row["reopen_condition"]:
                lines.append(f"  - reopen_condition: {row['reopen_condition']}")
    else:
        lines.append("- none")
    lines += ["", "## 未决假设"]
    if open_items:
        for row in open_items:
            evidence = ", ".join(json.loads(row["evidence_run_ids_json"]))
            lines.append(f"- {row['decision_id']}: {row['title']} evidence={evidence}")
            lines.append(f"  - {row['claim']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## 下一步最小实验集合",
        "1. 先运行 `auto-iteration route check --config <file> --summary <中文路线说明>`。",
        "2. 若允许，再运行实验并用 `auto-iteration run finish` 写回指标和工件。",
        "3. 实验后用 `auto-iteration decision add` 写入结论状态。",
        "",
        "## 读取顺序",
        f"1. {root() / 'AGENTS.md'}",
        f"2. {root() / 'handoffs' / 'latest_handoff.md'}",
        f"3. {root() / 'plans' / 'global_plan.md'}",
        f"4. {root() / 'plans' / 'version_iterations.md'}",
        f"5. {root() / 'plans' / 'active_plan.md'}",
        f"6. {root() / 'state' / 'agent_state.db'}",
        f"7. {root() / 'decisions'}",
        "8. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。",
        "",
    ]
    return "\n".join(lines), success["run_id"] if success else None


def command_handoff_generate(_args: argparse.Namespace) -> int:
    path = root() / "handoffs" / "latest_handoff.md"
    with database() as db:
        handoff_md, based_on_run_id = build_handoff(db)
        path.write_text(handoff_md, encoding="utf-8")
        archive = root() / "handoffs" / "archive" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        archive.write_text(handoff_md, encoding="utf-8")
        handoff_id = new_id("H")
        db.execute(
            """
            insert into handoffs (handoff_id, created_at, based_on_run_id, path, handoff_md)
            values (?, ?, ?, ?, ?)
            """,
            (handoff_id, now_iso(), based_on_run_id, str(path.resolve()), handoff_md),
        )
    print(f"generated {path.resolve()}")
    return 0


def command_resume(_args: argparse.Namespace) -> int:
    path = root() / "handoffs" / "latest_handoff.md"
    if not path.exists():
        print(f"handoff missing: {path.resolve()}")
        print("run `auto-iteration handoff generate` after at least one recorded run")
        return 1
    print(f"read first: {path.resolve()}")
    print(path.read_text(encoding="utf-8"))
    return 0


def add_common_run_subcommands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    run_parser = subparsers.add_parser("run")
    run_sub = run_parser.add_subparsers(dest="run_command", required=True)
    start = run_sub.add_parser("start")
    start.add_argument("--config", required=True)
    start.add_argument("--dataset", required=True)
    start.add_argument("--command", required=True)
    start.add_argument("--seed")
    start.add_argument("--session")
    start.set_defaults(func=command_run_start)
    exec_cmd = run_sub.add_parser("exec")
    exec_cmd.add_argument("--config", required=True)
    exec_cmd.add_argument("--dataset", required=True)
    exec_cmd.add_argument("--command", required=True)
    exec_cmd.add_argument("--metrics")
    exec_cmd.add_argument("--artifact", action="append", default=[])
    exec_cmd.add_argument("--seed")
    exec_cmd.add_argument("--session")
    exec_cmd.set_defaults(func=command_run_exec)
    finish = run_sub.add_parser("finish")
    finish.add_argument("run_id")
    finish.add_argument("--status", required=True)
    finish.add_argument("--metrics")
    finish.add_argument("--artifact", action="append", default=[])
    finish.set_defaults(func=command_run_finish)
    list_cmd = run_sub.add_parser("list")
    list_cmd.add_argument("--latest", type=int, default=10)
    list_cmd.set_defaults(func=command_run_list)
    show = run_sub.add_parser("show")
    show.add_argument("run_id")
    show.set_defaults(func=command_run_show)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-iteration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.set_defaults(func=command_init)
    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(func=command_doctor)
    install = subparsers.add_parser("install")
    install.add_argument("--bin-dir", default=str(default_bin_dir()))
    install.add_argument("--skills-dir", default=str(default_skills_dir()))
    install.set_defaults(func=command_install)
    add_common_run_subcommands(subparsers)
    decision = subparsers.add_parser("decision")
    decision_sub = decision.add_subparsers(dest="decision_command", required=True)
    add = decision_sub.add_parser("add")
    add.add_argument("--status", required=True)
    add.add_argument("--evidence", action="append", default=[])
    add.add_argument("--title", required=True)
    add.add_argument("--claim", required=True)
    add.add_argument("--route-keyword", action="append", default=[])
    add.add_argument("--reopen-condition")
    add.add_argument("--supersedes")
    add.set_defaults(func=command_decision_add)
    supersede = decision_sub.add_parser("supersede")
    supersede.add_argument("old_id")
    supersede.add_argument("--by", dest="new_id", required=True)
    supersede.set_defaults(func=command_decision_supersede)
    route = subparsers.add_parser("route")
    route_sub = route.add_subparsers(dest="route_command", required=True)
    check = route_sub.add_parser("check")
    check.add_argument("--config", required=True)
    check.add_argument("--summary", required=True)
    check.set_defaults(func=command_route_check)
    handoff = subparsers.add_parser("handoff")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    generate = handoff_sub.add_parser("generate")
    generate.set_defaults(func=command_handoff_generate)
    resume = subparsers.add_parser("resume")
    resume.set_defaults(func=command_resume)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
