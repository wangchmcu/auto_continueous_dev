import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(workdir, *args, check=True):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "auto_iteration.cli", *args],
        cwd=workdir,
        text=True,
        capture_output=True,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.tmp = Path(self.temp_dir.name)

    def test_init_and_doctor_create_state_store(self):
        result = run_cli(self.tmp, "init")

        self.assertIn("initialized", result.stdout)
        self.assertTrue((self.tmp / "state" / "agent_state.db").exists())
        self.assertTrue((self.tmp / "runs").is_dir())
        self.assertTrue((self.tmp / "raw_input").is_dir())
        self.assertTrue((self.tmp / "decisions" / "rejected").is_dir())
        self.assertTrue((self.tmp / "handoffs" / "archive").is_dir())
        self.assertTrue((self.tmp / "plans" / "global_plan.md").exists())
        self.assertTrue((self.tmp / "plans" / "active_plan.md").exists())
        self.assertTrue((self.tmp / "plans" / "version_iterations.md").exists())
        active_plan = (self.tmp / "plans" / "active_plan.md").read_text(encoding="utf-8")
        version_tracking = (self.tmp / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (self.tmp / "plans" / "global_plan.md").read_text(encoding="utf-8")
        self.assertIn("低假设初始化", active_plan)
        self.assertIn("当前业务目标：待用户定义", active_plan)
        self.assertIn("对话中途接入", active_plan)
        self.assertIn("candidate_checks", active_plan)
        self.assertIn("proposed_not_accepted", active_plan)
        self.assertIn("raw_input_source", active_plan)
        self.assertIn("初期输入源", active_plan)
        self.assertIn("current_version: bootstrap-v0", version_tracking)
        self.assertIn("status: pending_user_plan", version_tracking)
        self.assertIn("不要把 agent 推断写成正式路线", version_tracking)
        self.assertIn("context index --include-raw-input", version_tracking)
        self.assertIn("低假设项目初始化", global_plan)
        self.assertIn("来源标注", global_plan)
        self.assertIn("bootstrap checkpoint", global_plan)
        self.assertIn("raw_input 初期输入", global_plan)
        self.assertNotIn("当前版本：v0.8", active_plan)
        self.assertNotIn("v0.6 任务清单", version_tracking)
        self.assertNotIn("v0.7 任务清单", version_tracking)
        self.assertNotIn("v0.8 任务清单", version_tracking)
        self.assertNotIn("后续可选：语义检索", global_plan)

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn("state: ok", doctor.stdout)
        self.assertIn("database: ok", doctor.stdout)

    def test_install_creates_short_command_and_entry_skill(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"

        result = run_cli(
            self.tmp,
            "install",
            "--bin-dir",
            str(bin_dir),
            "--skills-dir",
            str(skills_dir),
        )

        command_path = bin_dir / "auto-iter"
        skill_path = skills_dir / "auto-iteration-entry" / "SKILL.md"
        improve_skill_path = skills_dir / "auto-it-self-improve" / "SKILL.md"
        self.assertTrue(command_path.exists())
        self.assertTrue(os.access(command_path, os.X_OK))
        self.assertTrue(skill_path.exists())
        self.assertTrue(improve_skill_path.exists())
        self.assertIn("installed command", result.stdout)
        self.assertIn("installed skill", result.stdout)
        self.assertIn("install check: ok", result.stdout)
        self.assertIn("dependency ready: python3", result.stdout)
        self.assertIn("command ready: auto-iter", result.stdout)
        self.assertIn("path hint:", result.stdout)
        self.assertIn("skill ready: auto-iteration-entry", result.stdout)
        self.assertIn("skill ready: auto-it-self-improve", result.stdout)
        skill_text = skill_path.read_text(encoding="utf-8")
        improve_skill_text = improve_skill_path.read_text(encoding="utf-8")
        self.assertIn("auto-iter doctor", skill_text)
        self.assertIn("结束当前 session", skill_text)
        self.assertIn("auto-iter intent check", skill_text)
        self.assertIn("中途记录一下", skill_text)
        self.assertIn("fixed tool and skill names", skill_text)
        self.assertIn("installed absolute command path", skill_text)
        self.assertIn("context index --include-raw-input", skill_text)
        self.assertIn("--allow-raw-input", skill_text)
        self.assertIn("raw_input_source", skill_text)
        self.assertIn("auto-iter uninstall", skill_text)
        self.assertIn("does not remove project state", skill_text)
        self.assertIn("--keep-project-state", skill_text)
        self.assertIn("--remove-project-state", skill_text)
        self.assertIn("auto it self improve", improve_skill_text)
        self.assertIn("Do not write concrete project details", improve_skill_text)
        self.assertIn("If skills changed, run the install command", improve_skill_text)
        self.assertIn("second-order", improve_skill_text)
        self.assertIn("self improve workflow itself", improve_skill_text)

        env = os.environ.copy()
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        doctor = subprocess.run(
            ["auto-iter", "doctor"],
            cwd=self.tmp,
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(doctor.returncode, 0)
        self.assertIn("state: ok", doctor.stdout)

    def test_uninstall_removes_installed_command_and_skills_only(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        run_cli(
            self.tmp,
            "install",
            "--bin-dir",
            str(bin_dir),
            "--skills-dir",
            str(skills_dir),
        )

        command_path = bin_dir / "auto-iter"
        entry_skill_path = skills_dir / "auto-iteration-entry"
        improve_skill_path = skills_dir / "auto-it-self-improve"

        result = run_cli(
            self.tmp,
            "uninstall",
            "--bin-dir",
            str(bin_dir),
            "--skills-dir",
            str(skills_dir),
        )

        self.assertIn("removed command", result.stdout)
        self.assertIn("removed skill: auto-iteration-entry", result.stdout)
        self.assertIn("removed skill: auto-it-self-improve", result.stdout)
        self.assertIn("Project state directories", result.stdout)
        self.assertIn("state/: SQLite", result.stdout)
        self.assertIn("project state preserved", result.stdout)
        self.assertFalse(command_path.exists())
        self.assertFalse(entry_skill_path.exists())
        self.assertFalse(improve_skill_path.exists())
        self.assertTrue((self.tmp / "state" / "agent_state.db").exists())
        self.assertTrue((self.tmp / "plans" / "active_plan.md").exists())
        self.assertTrue((self.tmp / "raw_input").is_dir())

    def test_uninstall_can_remove_project_state_when_explicitly_requested(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        run_cli(
            self.tmp,
            "install",
            "--bin-dir",
            str(bin_dir),
            "--skills-dir",
            str(skills_dir),
        )

        result = run_cli(
            self.tmp,
            "uninstall",
            "--bin-dir",
            str(bin_dir),
            "--skills-dir",
            str(skills_dir),
            "--remove-project-state",
        )

        self.assertIn("Project state directories", result.stdout)
        self.assertIn("raw_input/: original input", result.stdout)
        self.assertIn("removed project state: state", result.stdout)
        self.assertIn("removed project state: plans", result.stdout)
        self.assertIn("removed project state: raw_input", result.stdout)
        self.assertIn("removed project state: decisions", result.stdout)
        self.assertIn("removed project state: runs", result.stdout)
        self.assertIn("removed project state: handoffs", result.stdout)
        self.assertFalse((self.tmp / "state").exists())
        self.assertFalse((self.tmp / "plans").exists())
        self.assertFalse((self.tmp / "raw_input").exists())
        self.assertFalse((self.tmp / "decisions").exists())
        self.assertFalse((self.tmp / "runs").exists())
        self.assertFalse((self.tmp / "handoffs").exists())

    def test_topic_lifecycle_keeps_one_active_and_writes_projections(self):
        run_cli(self.tmp, "init")

        first = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic A",
            "--summary",
            "第一个 topic 的摘要",
        )
        first_topic_id = first.stdout.strip().split()[-1]
        current = run_cli(self.tmp, "topic", "current")

        self.assertIn("started topic", first.stdout)
        self.assertIn("Topic A", current.stdout)
        self.assertIn("active", current.stdout)
        self.assertIn("第一个 topic 的摘要", (self.tmp / "topics" / "active_topic.md").read_text(encoding="utf-8"))

        second = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic B",
            "--summary",
            "第二个 topic 的摘要",
            "--current-summary",
            "Topic A 当前现场",
        )
        second_topic_id = second.stdout.strip().split()[-1]
        listed = run_cli(self.tmp, "topic", "list")
        first_archive = self.tmp / "topics" / "archive" / f"{first_topic_id}.md"

        self.assertIn("Topic A", listed.stdout)
        self.assertIn("archived_open", listed.stdout)
        self.assertIn("Topic B", listed.stdout)
        self.assertIn("active", listed.stdout)
        self.assertTrue(first_archive.exists())
        self.assertIn("Topic A 当前现场", first_archive.read_text(encoding="utf-8"))
        self.assertIn("Topic B", (self.tmp / "topics" / "active_topic.md").read_text(encoding="utf-8"))

        switched = run_cli(
            self.tmp,
            "topic",
            "switch",
            "--topic-id",
            first_topic_id,
            "--current-summary",
            "Topic B 当前现场",
        )
        self.assertIn(f"switched topic {first_topic_id}", switched.stdout)
        self.assertIn("Topic A", run_cli(self.tmp, "topic", "current").stdout)
        self.assertIn("Topic B 当前现场", (self.tmp / "topics" / "archive" / f"{second_topic_id}.md").read_text(encoding="utf-8"))

        satisfied = run_cli(self.tmp, "topic", "satisfy", "--summary", "Topic A 阶段性达到预期")
        no_current = run_cli(self.tmp, "topic", "current", check=False)

        self.assertIn(f"satisfied topic {first_topic_id}", satisfied.stdout)
        self.assertEqual(no_current.returncode, 1)
        self.assertIn("no active topic", no_current.stderr)
        self.assertIn("archived_satisfied", run_cli(self.tmp, "topic", "list").stdout)
        self.assertIn("Topic A 阶段性达到预期", first_archive.read_text(encoding="utf-8"))

        with closing(sqlite3.connect(self.tmp / "state" / "agent_state.db")) as db:
            active_count = db.execute("select count(*) from topics where status = 'active'").fetchone()[0]
            event_names = [row[0] for row in db.execute("select event_type from topic_events order by created_at, rowid")]
        self.assertEqual(active_count, 0)
        self.assertIn("create", event_names)
        self.assertIn("archive_open", event_names)
        self.assertIn("switch_in", event_names)
        self.assertIn("archive_satisfied", event_names)

    def test_topic_context_handoff_and_entry_skill_are_indexed(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        installed = run_cli(self.tmp, "install", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))
        run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic Archive MVP",
            "--summary",
            "按 topic 归档并按需恢复上下文",
        )

        index = run_cli(self.tmp, "context", "index")
        handoff = run_cli(self.tmp, "handoff", "generate")
        handoff_text = (self.tmp / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        skill_text = (skills_dir / "auto-iteration-entry" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("topics/index.md", index.stdout)
        self.assertIn("topics/active_topic.md", index.stdout)
        self.assertIn("Topic Archive MVP", index.stdout)
        self.assertIn("generated", handoff.stdout)
        self.assertIn("active_topic", handoff_text)
        self.assertIn(str((self.tmp / "topics" / "active_topic.md").resolve()), handoff_text)
        self.assertIn("topic_index", handoff_text)
        self.assertIn(str((self.tmp / "topics" / "index.md").resolve()), handoff_text)
        self.assertIn("是不是已经切入新的 topic 了", skill_text)
        self.assertIn("auto-iter topic", skill_text)
        self.assertIn("install check: ok", installed.stdout)

    def test_run_finish_persists_config_metrics_and_artifacts(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "plot.txt"
        write_json(config, {"sample_count": 10000, "threshold": 0.65})
        write_json(
            metrics,
            {"precision": {"value": 0.91, "unit": "ratio", "direction": "higher_is_better"}},
        )
        artifact.write_text("plot placeholder\n", encoding="utf-8")

        started = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "demo-set",
            "--command",
            "python experiment.py",
        )
        run_id = started.stdout.strip().split()[-1]

        run_cli(
            self.tmp,
            "run",
            "finish",
            run_id,
            "--status",
            "success",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        shown = run_cli(self.tmp, "run", "show", run_id)

        self.assertIn("sample_count", shown.stdout)
        self.assertIn("precision", shown.stdout)
        self.assertIn(str(artifact.resolve()), shown.stdout)

        with closing(sqlite3.connect(self.tmp / "state" / "agent_state.db")) as db:
            metric = db.execute(
                "select metric_value, unit, direction from metrics where run_id = ? and metric_name = ?",
                (run_id, "precision"),
            ).fetchone()
        self.assertEqual(metric, (0.91, "ratio", "higher_is_better"))
        self.assertTrue((self.tmp / "runs" / run_id / "summary.md").exists())
        self.assertTrue((self.tmp / "runs" / run_id / "logs" / "error_summary.md").exists())
        self.assertTrue((self.tmp / "runs" / run_id / "logs" / "stdout.log").exists())
        self.assertTrue((self.tmp / "runs" / run_id / "logs" / "stderr.log").exists())
        self.assertTrue((self.tmp / "runs" / run_id / "logs" / "debug.jsonl").exists())

    def test_run_exec_captures_logs_and_generates_summaries(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        script = self.tmp / "experiment.py"
        write_json(config, {"sample_count": 50, "threshold": 0.42})
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "import json",
                    "import sys",
                    "metrics = Path(sys.argv[1])",
                    "artifact = Path(sys.argv[2])",
                    "print('stdout marker')",
                    "print('stderr marker', file=sys.stderr)",
                    "metrics.write_text(json.dumps({'score': {'value': 0.75, 'unit': 'ratio', 'direction': 'higher_is_better'}}), encoding='utf-8')",
                    "artifact.write_text('# report\\n', encoding='utf-8')",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_cli(
            self.tmp,
            "run",
            "exec",
            "--config",
            str(config),
            "--dataset",
            "exec-demo",
            "--command",
            f"{sys.executable} {script} {metrics} {artifact}",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        run_id = result.stdout.strip().split()[2]
        run_dir = self.tmp / "runs" / run_id

        self.assertIn("status=success", result.stdout)
        self.assertIn("stdout marker", (run_dir / "logs" / "stdout.log").read_text(encoding="utf-8"))
        self.assertIn("stderr marker", (run_dir / "logs" / "stderr.log").read_text(encoding="utf-8"))
        self.assertIn('"event": "finished"', (run_dir / "logs" / "debug.jsonl").read_text(encoding="utf-8"))
        self.assertIn("score", (run_dir / "summary.md").read_text(encoding="utf-8"))
        self.assertIn("stderr marker", (run_dir / "logs" / "error_summary.md").read_text(encoding="utf-8"))

    def test_run_exec_records_failed_run_and_error_summary(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        write_json(config, {"case": "failure"})

        result = run_cli(
            self.tmp,
            "run",
            "exec",
            "--config",
            str(config),
            "--dataset",
            "exec-demo",
            "--command",
            f"{sys.executable} -c \"import sys; print('fatal detail', file=sys.stderr); sys.exit(3)\"",
            check=False,
        )
        run_id = result.stdout.strip().split()[2]
        run_dir = self.tmp / "runs" / run_id

        self.assertEqual(result.returncode, 3)
        self.assertIn("status=failed", result.stdout)
        self.assertIn("fatal detail", (run_dir / "logs" / "stderr.log").read_text(encoding="utf-8"))
        self.assertIn("fatal detail", (run_dir / "logs" / "error_summary.md").read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.tmp / "state" / "agent_state.db")) as db:
            status = db.execute("select status from runs where run_id = ?", (run_id,)).fetchone()[0]
        self.assertEqual(status, "failed")

    def test_v0_2_entry_flow_uses_installed_auto_iter_command(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        run_cli(self.tmp, "install", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))

        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        script = self.tmp / "experiment.py"
        write_json(config, {"round": 1, "method": "entry-flow"})
        script.write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    "import json",
                    "import sys",
                    "Path(sys.argv[1]).write_text(json.dumps({'loss': 0.2}), encoding='utf-8')",
                    "Path(sys.argv[2]).write_text('# v0.2 demo report\\n', encoding='utf-8')",
                    "print('entry flow complete')",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

        def run_auto_iter(*args, check=True):
            result = subprocess.run(
                ["auto-iter", *args],
                cwd=self.tmp,
                text=True,
                capture_output=True,
                env=env,
            )
            if check and result.returncode != 0:
                raise AssertionError(
                    f"auto-iter failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
            return result

        self.assertIn("state: ok", run_auto_iter("doctor").stdout)
        self.assertIn("handoff", run_auto_iter("resume", check=False).stdout)
        self.assertIn(
            "ALLOWED",
            run_auto_iter("route", "check", "--config", str(config), "--summary", "v0.2 入口流程演示").stdout,
        )
        executed = run_auto_iter(
            "run",
            "exec",
            "--config",
            str(config),
            "--dataset",
            "v0.2-entry-demo",
            "--command",
            f"{sys.executable} {script} {metrics} {artifact}",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        run_id = executed.stdout.strip().split()[2]
        run_auto_iter(
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "v0.2 入口流程演示通过",
            "--claim",
            "Codex agent 可以在同一会话内通过 auto-iter 完成恢复、路线检查、执行实验、记录结论和生成 handoff。",
        )
        run_auto_iter("handoff", "generate")

        handoff = (self.tmp / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("global_plan", handoff)
        self.assertIn("v0.2 入口流程演示通过", handoff)
        self.assertIn("entry flow complete", (self.tmp / "runs" / run_id / "logs" / "stdout.log").read_text(encoding="utf-8"))

    def test_rejected_decision_blocks_matching_route(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        write_json(config, {"sample_count": 100000, "proposal": "brute_force"})
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "demo-set",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]

        run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "rejected",
            "--evidence",
            run_id,
            "--title",
            "放弃单纯提高采样次数到 100000",
            "--claim",
            "收益太小，运行时间增加过多。",
            "--route-keyword",
            "采样次数",
            "--route-keyword",
            "100000",
            "--reopen-condition",
            "只有当并行化成本下降五倍以上时才允许重开。",
        )

        blocked = run_cli(
            self.tmp,
            "route",
            "check",
            "--config",
            str(config),
            "--summary",
            "再次把采样次数提高到 100000",
            check=False,
        )

        self.assertEqual(blocked.returncode, 2)
        self.assertIn("BLOCKED", blocked.stdout)
        self.assertIn("放弃单纯提高采样次数到 100000", blocked.stdout)
        self.assertIn(run_id, blocked.stdout)

    def test_route_check_blocks_rejected_parameter_space(self):
        run_cli(self.tmp, "init")
        evidence_config = self.tmp / "evidence.json"
        blocked_config = self.tmp / "blocked.json"
        allowed_config = self.tmp / "allowed.json"
        write_json(evidence_config, {"threshold": 0.75, "method": "weighted"})
        write_json(blocked_config, {"threshold": 0.72, "method": "weighted"})
        write_json(allowed_config, {"threshold": 0.45, "method": "weighted"})
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(evidence_config),
            "--dataset",
            "route-space",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]

        run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "rejected",
            "--evidence",
            run_id,
            "--title",
            "放弃 weighted 方法的高阈值区间",
            "--claim",
            "threshold 在 0.60 到 0.90 之间时稳定性差。",
            "--route-relation",
            "parameter-space",
            "--route-keyword",
            "weighted",
            "--route-param",
            "threshold:0.60:0.90",
            "--reopen-condition",
            "只有更换打分函数后才允许重开。",
        )

        blocked = run_cli(
            self.tmp,
            "route",
            "check",
            "--config",
            str(blocked_config),
            "--summary",
            "继续尝试 weighted 方法 threshold 0.72",
            check=False,
        )
        allowed = run_cli(
            self.tmp,
            "route",
            "check",
            "--config",
            str(allowed_config),
            "--summary",
            "继续尝试 weighted 方法 threshold 0.45",
        )

        self.assertEqual(blocked.returncode, 2)
        self.assertIn("parameter-space", blocked.stdout)
        self.assertIn("threshold:0.6:0.9", blocked.stdout)
        self.assertIn("BLOCKED", blocked.stdout)
        self.assertIn("ALLOWED", allowed.stdout)

    def test_handoff_validate_reports_missing_required_sections(self):
        run_cli(self.tmp, "init")
        valid = run_cli(self.tmp, "handoff", "generate")

        self.assertIn("generated", valid.stdout)
        validated = run_cli(self.tmp, "handoff", "validate")
        self.assertIn("VALID", validated.stdout)

        handoff_path = self.tmp / "handoffs" / "latest_handoff.md"
        text = handoff_path.read_text(encoding="utf-8").replace("## 读取顺序", "## Broken Read Order")
        handoff_path.write_text(text, encoding="utf-8")
        invalid = run_cli(self.tmp, "handoff", "validate", check=False)

        self.assertEqual(invalid.returncode, 1)
        self.assertIn("INVALID", invalid.stdout)
        self.assertIn("missing section: ## 读取顺序", invalid.stdout)

    def test_context_index_and_show_exclude_raw_input_by_default(self):
        run_cli(self.tmp, "init")
        raw_note = self.tmp / "raw_input" / "legacy.md"
        raw_archive = self.tmp / "raw_input" / "legacy.mhtml"
        raw_note.write_text("# Legacy Raw Input\n\nlegacy-only detail\n", encoding="utf-8")
        raw_archive.write_text("<html><body>archived source detail</body></html>\n", encoding="utf-8")

        index = run_cli(self.tmp, "context", "index")
        raw_index = run_cli(self.tmp, "context", "index", "--include-raw-input")
        shown = run_cli(
            self.tmp,
            "context",
            "show",
            "--path",
            str(self.tmp / "plans" / "global_plan.md"),
            "--heading",
            "Global Plan",
        )
        blocked_raw = run_cli(
            self.tmp,
            "context",
            "show",
            "--path",
            str(raw_note),
            "--heading",
            "Legacy Raw Input",
            check=False,
        )
        allowed_raw = run_cli(
            self.tmp,
            "context",
            "show",
            "--path",
            str(raw_note),
            "--heading",
            "Legacy Raw Input",
            "--allow-raw-input",
        )

        self.assertIn("plans/global_plan.md", index.stdout)
        self.assertNotIn("legacy-only detail", index.stdout)
        self.assertNotIn("raw_input/legacy.md", index.stdout)
        self.assertIn("raw_input/legacy.md", raw_index.stdout)
        self.assertIn("raw_input/legacy.mhtml", raw_index.stdout)
        self.assertIn("no markdown headings", raw_index.stdout)
        self.assertIn("# Global Plan", shown.stdout)
        self.assertEqual(blocked_raw.returncode, 1)
        self.assertIn("raw_input requires --allow-raw-input", blocked_raw.stderr)
        self.assertIn("legacy-only detail", allowed_raw.stdout)

    def test_intent_check_suggests_safe_checkpoints_without_writing_state(self):
        run_cli(self.tmp, "init")

        before_execution = run_cli(self.tmp, "intent", "check", "--text", "确定执行，先跑实验")
        after_result = run_cli(self.tmp, "intent", "check", "--text", "拿到结果了，测试结束了")
        mid_session_record = run_cli(self.tmp, "intent", "check", "--text", "中途记录一下当前状态")

        self.assertIn("INTENT CHECKPOINT", before_execution.stdout)
        self.assertIn("intent: pre-execution", before_execution.stdout)
        self.assertIn("auto-iter route check", before_execution.stdout)
        self.assertIn("do not run or record only from this keyword", before_execution.stdout)
        self.assertIn("intent: post-result", after_result.stdout)
        self.assertIn("metrics", after_result.stdout)
        self.assertIn("auto-iter decision add", after_result.stdout)
        self.assertIn("intent: mid-session-record", mid_session_record.stdout)
        self.assertIn("auto-iter checkpoint save", mid_session_record.stdout)
        self.assertIn("do not commit or push unless the user explicitly asks", mid_session_record.stdout)

    def test_checkpoint_save_generates_valid_handoff_without_commit_push(self):
        run_cli(self.tmp, "init")

        checkpoint = run_cli(self.tmp, "checkpoint", "save", "--text", "中途记录一下当前状态")

        handoff_path = self.tmp / "handoffs" / "latest_handoff.md"
        self.assertIn("CHECKPOINT SAVED", checkpoint.stdout)
        self.assertIn("handoff_valid: yes", checkpoint.stdout)
        self.assertIn("commit_push: not requested", checkpoint.stdout)
        self.assertIn(str(handoff_path.resolve()), checkpoint.stdout)
        self.assertTrue(handoff_path.exists())
        self.assertIn("## 当前快照", handoff_path.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.tmp / "state" / "agent_state.db")) as db:
            count = db.execute("select count(*) from handoffs").fetchone()[0]
        self.assertEqual(count, 1)

    def test_handoff_and_resume_include_absolute_evidence_paths(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        write_json(config, {"threshold": 0.58})
        write_json(metrics, {"recall": 0.87})
        artifact.write_text("# report\n", encoding="utf-8")
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "rain-demo",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        run_cli(
            self.tmp,
            "run",
            "finish",
            run_id,
            "--status",
            "success",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "雨天阈值使用 0.58",
            "--claim",
            "雨天样本 recall 达到 0.87。",
        )

        handoff = run_cli(self.tmp, "handoff", "generate")
        resume = run_cli(self.tmp, "resume")

        handoff_path = self.tmp / "handoffs" / "latest_handoff.md"
        text = handoff_path.read_text(encoding="utf-8")
        self.assertIn(str(handoff_path.resolve()), handoff.stdout)
        self.assertIn("## 当前目标", text)
        self.assertIn("global_plan", text)
        self.assertIn(str((self.tmp / "plans" / "global_plan.md").resolve()), text)
        self.assertIn("version_task_tracking", text)
        self.assertIn(str((self.tmp / "plans" / "version_iterations.md").resolve()), text)
        self.assertIn("## 当前有效结论", text)
        self.assertIn("雨天阈值使用 0.58", text)
        self.assertIn(str(artifact.resolve()), text)
        self.assertIn(str(handoff_path.resolve()), resume.stdout)

    def test_handoff_uses_newest_success_when_runs_share_timestamp(self):
        run_cli(self.tmp, "init")
        first_config = self.tmp / "first.json"
        second_config = self.tmp / "second.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        write_json(first_config, {"round": 1})
        write_json(second_config, {"round": 2})
        write_json(metrics, {"score": 1.0})
        artifact.write_text("# report\n", encoding="utf-8")

        first_run = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(first_config),
            "--dataset",
            "same-second",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        run_cli(
            self.tmp,
            "run",
            "finish",
            first_run,
            "--status",
            "success",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        second_run = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(second_config),
            "--dataset",
            "same-second",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        run_cli(
            self.tmp,
            "run",
            "finish",
            second_run,
            "--status",
            "success",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )
        with closing(sqlite3.connect(self.tmp / "state" / "agent_state.db")) as db:
            db.execute("update runs set ended_at = '2026-01-01T00:00:00+00:00'")
            db.commit()

        run_cli(self.tmp, "handoff", "generate")

        text = (self.tmp / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn(f"latest_successful_run_id: {second_run}", text)


if __name__ == "__main__":
    unittest.main()
