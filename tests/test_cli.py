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
        self.assertTrue((self.tmp / "decisions" / "rejected").is_dir())
        self.assertTrue((self.tmp / "handoffs" / "archive").is_dir())
        self.assertTrue((self.tmp / "plans" / "active_plan.md").exists())
        self.assertTrue((self.tmp / "plans" / "version_iterations.md").exists())

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn("state: ok", doctor.stdout)
        self.assertIn("database: ok", doctor.stdout)

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
