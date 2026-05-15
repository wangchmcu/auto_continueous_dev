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
DECISION_STATUSES = {"active", "rejected", "superseded", "open"}
RUN_STATUSES = {"running", "success", "failed", "aborted"}


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
    print("state: ok")
    with database() as db:
        row = db.execute("select count(*) from sqlite_master where type = 'table'").fetchone()
    if row[0] < 7:
        raise UserError("database schema is incomplete")
    print("database: ok")
    print(f"root: {root()}")
    return 0


def new_id(prefix: str) -> str:
    value = hashlib.sha256(f"{prefix}:{now_iso()}:{os.getpid()}:{root()}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{value}"


def command_run_start(args: argparse.Namespace) -> int:
    config = read_json(args.config)
    run_id = new_id("R")
    run_dir = root() / "runs" / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    config_text = json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True)
    (run_dir / "config_resolved.json").write_text(config_text + "\n", encoding="utf-8")
    config_hash = hash_data(config)
    with database() as db:
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
                args.session,
                git_commit(),
                git_branch(),
                args.dataset,
                args.seed,
                args.command,
                stable_json(config),
                config_hash,
                now_iso(),
            ),
        )
    print(f"started run {run_id}")
    return 0


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


def command_run_finish(args: argparse.Namespace) -> int:
    if args.status not in RUN_STATUSES:
        raise UserError(f"invalid status: {args.status}")
    metrics = read_json(args.metrics) if args.metrics else {}
    with database() as db:
        existing = db.execute("select run_id from runs where run_id = ?", (args.run_id,)).fetchone()
        if not existing:
            raise UserError(f"unknown run_id: {args.run_id}")
        for name, raw_value in metrics.items():
            value, unit, direction = normalize_metric(raw_value)
            db.execute(
                """
                insert or replace into metrics (run_id, metric_name, metric_value, unit, direction)
                values (?, ?, ?, ?, ?)
                """,
                (args.run_id, name, value, unit, direction),
            )
        for path in args.artifact:
            add_artifact(db, args.run_id, path)
        summary = f"status={args.status}; metrics={', '.join(sorted(metrics))}"
        db.execute(
            "update runs set status = ?, ended_at = ?, summary = ? where run_id = ?",
            (args.status, now_iso(), summary, args.run_id),
        )
    print(f"finished run {args.run_id}")
    return 0


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
        f"3. {root() / 'state' / 'agent_state.db'}",
        f"4. {root() / 'decisions'}",
        "5. 只有调查具体失败时才读取 runs/<run_id>/logs/ 下的原始日志。",
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
