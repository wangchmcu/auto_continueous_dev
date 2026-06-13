import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path, PureWindowsPath

from auto_iteration import cli


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(workdir, *args, check=True, env_extra=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    if env_extra:
        env.update(env_extra)
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
        state_root = self.tmp / ".auto_iter"
        self.assertTrue((state_root / "state" / "agent_state.db").exists())
        self.assertTrue((state_root / "runs").is_dir())
        self.assertTrue((state_root / "raw_input").is_dir())
        self.assertTrue((state_root / "decisions" / "rejected").is_dir())
        self.assertTrue((state_root / "rules" / "active").is_dir())
        self.assertTrue((state_root / "handoffs" / "archive").is_dir())
        self.assertTrue((state_root / "plans" / "global_plan.md").exists())
        self.assertTrue((state_root / "plans" / "project_plan.md").exists())
        self.assertTrue((state_root / "plans" / "project_record_rules.md").exists())
        self.assertTrue((state_root / "plans" / "active_plan.md").exists())
        self.assertTrue((state_root / "plans" / "version_iterations.md").exists())
        self.assertFalse((self.tmp / "state").exists())
        self.assertFalse((self.tmp / "plans").exists())
        active_plan = (state_root / "plans" / "active_plan.md").read_text(encoding="utf-8")
        version_tracking = (state_root / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (state_root / "plans" / "global_plan.md").read_text(encoding="utf-8")
        project_plan = (state_root / "plans" / "project_plan.md").read_text(encoding="utf-8")
        project_record_rules = (state_root / "plans" / "project_record_rules.md").read_text(encoding="utf-8")
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
        self.assertIn("compatibility entry", global_plan)
        self.assertIn("plans/project_plan.md", global_plan)
        self.assertIn("plans/project_record_rules.md", global_plan)
        self.assertIn("AIT 工具自身迭代", global_plan)
        self.assertIn("低假设项目初始化", project_plan)
        self.assertIn("来源标注", project_plan)
        self.assertIn("bootstrap checkpoint", project_plan)
        self.assertIn("raw_input 初期输入", project_plan)
        self.assertIn("Project Record Rules", project_record_rules)
        self.assertIn("项目定制规则", project_record_rules)
        self.assertIn("不能记录 AIT 工具自身功能迭代任务", project_record_rules)
        self.assertNotIn("当前版本：v0.8", active_plan)
        self.assertNotIn("v0.6 任务清单", version_tracking)
        self.assertNotIn("v0.7 任务清单", version_tracking)
        self.assertNotIn("v0.8 任务清单", version_tracking)
        self.assertNotIn("后续可选：语义检索", project_plan)

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn("state: ok", doctor.stdout)
        self.assertIn("database: ok", doctor.stdout)
        self.assertIn(f"state_dir: {state_root}", doctor.stdout)
        self.assertIn("layout: single-dir", doctor.stdout)

    def test_legacy_layout_init_remains_available(self):
        result = run_cli(self.tmp, "init", "--legacy-layout")

        self.assertIn("initialized", result.stdout)
        self.assertTrue((self.tmp / "state" / "agent_state.db").exists())
        self.assertTrue((self.tmp / "plans" / "active_plan.md").exists())

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn(f"state_dir: {self.tmp}", doctor.stdout)
        self.assertIn("layout: legacy", doctor.stdout)

    def test_commands_from_subdirectory_use_nearest_project_root(self):
        run_cli(self.tmp, "init")
        subdir = self.tmp / "nested" / "workdir"
        subdir.mkdir(parents=True)

        doctor = run_cli(subdir, "doctor")

        self.assertIn("state: ok", doctor.stdout)
        self.assertIn(f"root: {self.tmp}", doctor.stdout)

        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        cwd_marker = self.tmp / "cwd.txt"
        write_json(config, {"round": 1, "method": "subdir-root"})
        write_json(metrics, {"ok": 1})
        artifact.write_text("# subdir root report\n", encoding="utf-8")

        executed = run_cli(
            subdir,
            "run",
            "exec",
            "--config",
            str(config),
            "--dataset",
            "subdir-root-demo",
            "--command",
            (
                f"{sys.executable} -c "
                f"\"from pathlib import Path; import os; "
                f"Path(r'{cwd_marker}').write_text(os.getcwd(), encoding='utf-8')\""
            ),
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
        )

        self.assertIn("status=success", executed.stdout)
        self.assertEqual(str(subdir), cwd_marker.read_text(encoding="utf-8"))
        self.assertEqual(1, len(list((self.tmp / ".auto_iter" / "runs").glob("R-*"))))
        self.assertFalse((subdir / "runs").exists())

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

    def test_project_root_cli_arg_overrides_cwd(self):
        run_cli(self.tmp, "init")
        sibling = self.tmp.parent / f"{self.tmp.name}_project_root_cli"
        sibling.mkdir()

        doctor = run_cli(sibling, "--project-root", str(self.tmp), "doctor")

        self.assertIn(f"root: {self.tmp}", doctor.stdout)
        self.assertIn(f"state_dir: {self.tmp / '.auto_iter'}", doctor.stdout)

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
        head = subprocess.run(
            ["git", "-C", str(workdir), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertIn(f"git_commit: {head}", summary)
        self.assertIn("git_branch: exp", summary)
        self.assertIn("git_dirty_count: 0", summary)
        self.assertIn(f"workdir: {workdir}", summary)

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

    def test_global_workdir_arg_controls_doctor_context(self):
        run_cli(self.tmp, "init")
        workdir = self.tmp / "worktrees" / "global-doctor"
        workdir.mkdir(parents=True)

        doctor = run_cli(self.tmp, "--workdir", str(workdir), "doctor")

        self.assertIn(f"root: {self.tmp}", doctor.stdout)
        self.assertIn(f"workdir: {workdir}", doctor.stdout)
        self.assertIn("workdir_source: cli", doctor.stdout)

    def test_handoff_snapshot_includes_workdir(self):
        run_cli(self.tmp, "init")
        workdir = self.tmp / "worktrees" / "handoff-workdir"
        workdir.mkdir(parents=True)

        run_cli(self.tmp, "handoff", "generate", env_extra={"AUTO_ITER_WORKDIR": str(workdir)})
        text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")

        self.assertIn(f"- root: {self.tmp}", text)
        self.assertIn(f"- workdir: {workdir}", text)

    def test_global_workdir_arg_controls_handoff_context(self):
        run_cli(self.tmp, "init")
        workdir = self.tmp / "worktrees" / "handoff-global-workdir"
        workdir.mkdir(parents=True)

        run_cli(self.tmp, "--workdir", str(workdir), "handoff", "generate")
        text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")

        self.assertIn(f"- root: {self.tmp}", text)
        self.assertIn(f"- workdir: {workdir}", text)

    def test_doctor_reports_no_resolved_topic_without_default(self):
        run_cli(self.tmp, "init")

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn("resolved_topic_id: none", doctor.stdout)
        self.assertIn("resolved_topic_source: none", doctor.stdout)

    def test_doctor_resolves_default_topic_when_no_override_exists(self):
        run_cli(self.tmp, "init")
        started = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Default Topic",
            "--summary",
            "Default topic summary",
        )
        topic_id = started.stdout.strip().split()[-1]

        doctor = run_cli(self.tmp, "doctor")

        self.assertIn(f"resolved_topic_id: {topic_id}", doctor.stdout)
        self.assertIn("resolved_topic_source: default_topic", doctor.stdout)

    def test_doctor_resolves_topic_from_environment_before_default(self):
        run_cli(self.tmp, "init")
        first = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic A",
            "--summary",
            "Topic A summary",
        )
        topic_a = first.stdout.strip().split()[-1]
        run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic B",
            "--summary",
            "Topic B summary",
            "--current-summary",
            "Switch from Topic A",
        )

        doctor = run_cli(self.tmp, "doctor", env_extra={"AUTO_ITER_TOPIC_ID": topic_a})

        self.assertIn(f"resolved_topic_id: {topic_a}", doctor.stdout)
        self.assertIn("resolved_topic_source: environment", doctor.stdout)

    def test_doctor_resolves_explicit_topic_before_environment(self):
        run_cli(self.tmp, "init")
        first = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic A",
            "--summary",
            "Topic A summary",
        )
        topic_a = first.stdout.strip().split()[-1]
        second = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic B",
            "--summary",
            "Topic B summary",
            "--current-summary",
            "Switch from Topic A",
        )
        topic_b = second.stdout.strip().split()[-1]

        doctor = run_cli(
            self.tmp,
            "doctor",
            "--topic-id",
            topic_b,
            env_extra={"AUTO_ITER_TOPIC_ID": topic_a},
        )

        self.assertIn(f"resolved_topic_id: {topic_b}", doctor.stdout)
        self.assertIn("resolved_topic_source: argument", doctor.stdout)

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
        self.assertIn("dependency ready: python", result.stdout)
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
        self.assertIn("auto-iter topic board", skill_text)
        self.assertIn("auto-iter handoff generate --topic-id", skill_text)
        self.assertIn("auto-iter migrate", skill_text)
        self.assertIn("--allow-raw-input", skill_text)
        self.assertIn("raw_input_source", skill_text)
        self.assertIn("Current Baseline", skill_text)
        self.assertIn("project-root `AGENTS.md`", skill_text)
        self.assertIn("does not create project-root `AGENTS.md`", skill_text)
        self.assertIn("auto-iter uninstall", skill_text)
        self.assertIn("auto-iter update", skill_text)
        self.assertIn("does not remove project state", skill_text)
        self.assertIn("--keep-project-state", skill_text)
        self.assertIn("--remove-project-state", skill_text)
        self.assertIn("already on `PATH` and writable", skill_text)
        self.assertIn("without explicit user opt-in", skill_text)
        self.assertIn("plans/version_iterations.md", skill_text)
        self.assertIn("global plan backlog", skill_text)
        self.assertIn("do not start a separate plan branch", skill_text)
        self.assertIn("auto-iter topic link", skill_text)
        self.assertIn("auto-iter topic evidence", skill_text)
        self.assertIn("auto-iter search query", skill_text)
        self.assertIn("BM25", skill_text)
        self.assertIn("auto it self improve", improve_skill_text)
        self.assertIn("Do not write concrete project details", improve_skill_text)
        self.assertIn("If skills changed, run the install command", improve_skill_text)
        self.assertIn("second-order", improve_skill_text)
        self.assertIn("self improve workflow itself", improve_skill_text)
        self.assertIn("Search the auto_iteration history", improve_skill_text)
        self.assertIn("Classify the scope before patching", improve_skill_text)
        self.assertIn("Bug: the prior plan", improve_skill_text)
        self.assertIn("Feature gap", improve_skill_text)
        self.assertIn("First principles", improve_skill_text)
        self.assertIn("source of truth", improve_skill_text)

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

    def test_source_global_plan_names_future_backlog(self):
        global_plan = (REPO_ROOT / "plans" / "global_plan.md").read_text(encoding="utf-8")

        self.assertIn("## 后续 Backlog", global_plan)
        self.assertIn("semantic retrieval", global_plan)
        self.assertIn("topic evidence link", global_plan)
        self.assertIn("topic lifecycle management", global_plan)
        self.assertIn("v0.19", global_plan)
        self.assertIn("auto-iter search query", global_plan)

    def test_topic_id_rollout_records_practice_bug_triage_rule(self):
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        self.assertIn("v0.23-v0.32 实践期问题判定规则", version_tracking)
        self.assertIn("功能 bug", version_tracking)
        self.assertIn("功能缺失", version_tracking)
        self.assertIn("不重新开 global plan 分支", version_tracking)
        self.assertIn("实践期问题判定规则", active_plan)

    def test_topic_pitfall_carryover_rule_is_documented(self):
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        entry_skill = (REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md").read_text(encoding="utf-8")
        workflow_skill = (REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")

        for text in [agents, entry_skill, workflow_skill, readme]:
            self.assertIn("topic evidence carryover check", text)
            self.assertIn("topic plan alone is not enough", text)
            self.assertIn("current branch or worktree", text)
        self.assertIn("v0.34", version_tracking)
        self.assertIn("topic evidence carryover check", version_tracking)

    def test_project_plan_split_and_ait_ownership_routing_are_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (REPO_ROOT / "plans" / "global_plan.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("plans/project_plan.md", text, str(path))
            self.assertIn("plans/project_record_rules.md", text, str(path))
            self.assertIn("ownership-routing", text, str(path))
            self.assertIn("Do not write AIT tool work into the managed project's project plan or topic plan", text, str(path))
        for text in [version_tracking, global_plan, active_plan]:
            self.assertIn("project plan split", text)
            self.assertIn("ownership-routing", text)
            self.assertIn("project_record_rules", text)

    def test_single_dir_layout_is_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (REPO_ROOT / "plans" / "global_plan.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn(".auto_iter", text, str(path))
            self.assertIn("migrate --layout single-dir", text, str(path))
        for text in [version_tracking, global_plan, active_plan]:
            self.assertIn("v0.38", text)
            self.assertIn(".auto_iter", text)
            self.assertIn("project state single-dir layout", text)

    def test_rule_tracking_is_documented(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        self.assertIn("## Rule tracking", readme)
        self.assertIn("auto-iter rule add", readme)
        self.assertIn("rules/current_effective.md", readme)
        self.assertIn("context index", readme)
        self.assertIn("search query", readme)
        self.assertIn("auto-iter rule add", agents)
        self.assertIn("rules/current_effective.md", agents)
        self.assertIn("v0.38", version_tracking)
        self.assertIn("rule add/list/show", version_tracking)
        self.assertIn("rules/current_effective.md", version_tracking)
        self.assertIn("rule tracking", active_plan)
        self.assertIn("rules/current_effective.md", active_plan)

    def test_project_topic_explicit_tracking_is_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (REPO_ROOT / "plans" / "global_plan.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("project link-topic", text, str(path))
            self.assertIn("bidirectional tracking", text, str(path))
            self.assertIn("not automatic", text, str(path))
        for text in [version_tracking, global_plan, active_plan]:
            self.assertIn("v0.40", text)
            self.assertIn("project-topic explicit tracking", text)
            self.assertIn("not", text)

    def test_old_project_migration_after_update_is_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Old project migration after AIT update", readme)
        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("auto-iter update --check-project", text, str(path))
            self.assertIn("auto-iter migrate", text, str(path))
            self.assertIn("auto-iter migrate --layout single-dir", text, str(path))
            self.assertIn("auto-iter handoff validate", text, str(path))
            self.assertIn("Do not run `init`", text, str(path))

    def test_rejected_experiment_recording_is_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        version_tracking = (REPO_ROOT / "plans" / "version_iterations.md").read_text(encoding="utf-8")
        global_plan = (REPO_ROOT / "plans" / "global_plan.md").read_text(encoding="utf-8")
        active_plan = (REPO_ROOT / "plans" / "active_plan.md").read_text(encoding="utf-8")

        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("auto-iter run import", text, str(path))
            self.assertIn("rejected experiment", text, str(path))
            self.assertIn("reopen-condition", text, str(path))
        for text in [version_tracking, global_plan, active_plan]:
            self.assertIn("v0.41", text)
            self.assertIn("rejected experiment", text)
            self.assertIn("run import", text)

    def test_worktree_execution_context_is_documented(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
        ]
        plan_files = [
            REPO_ROOT / "plans" / "version_iterations.md",
            REPO_ROOT / "plans" / "global_plan.md",
            REPO_ROOT / "plans" / "active_plan.md",
        ]

        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("AUTO_ITER_PROJECT_ROOT", text, str(path))
            self.assertIn("AUTO_ITER_WORKDIR", text, str(path))
            self.assertIn("--project-root", text, str(path))
            self.assertIn("--workdir", text, str(path))
            self.assertIn("shared AIT project root", text, str(path))
            self.assertIn("run summary", text, str(path))
        for path in plan_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("v0.42", text, str(path))
            self.assertIn("AUTO_ITER_PROJECT_ROOT", text, str(path))
            self.assertIn("AUTO_ITER_WORKDIR", text, str(path))
            self.assertIn("workdir", text, str(path))

    def test_command_wrappers_are_platform_aware(self):
        posix = cli.command_wrapper_spec(Path("/repo/tools/auto_iter.py"), platform_name="posix")
        windows = cli.command_wrapper_spec(PureWindowsPath("C:/repo/tools/auto_iter.py"), platform_name="windows")

        self.assertEqual(posix.filename, "auto-iter")
        self.assertIn("#!/usr/bin/env sh", posix.text)
        self.assertIn(str(Path("/repo/tools/auto_iter.py")), posix.text)
        self.assertIn('"$@"', posix.text)
        self.assertTrue(posix.executable)

        self.assertEqual(windows.filename, "auto-iter.cmd")
        self.assertIn("@echo off", windows.text)
        self.assertIn("C:\\repo\\tools\\auto_iter.py", windows.text)
        self.assertIn("%*", windows.text)
        self.assertFalse(windows.executable)

    def test_recommended_bin_dir_prefers_writable_standard_path_already_on_path(self):
        home = self.tmp / "home"
        homebrew_bin = self.tmp / "opt" / "homebrew" / "bin"
        local_bin = home / ".local" / "bin"
        path_text = os.pathsep.join([str(homebrew_bin), str(local_bin)])

        selected = cli.recommended_bin_dir(
            platform_name="posix",
            path_text=path_text,
            home=home,
            is_writable=lambda path: path == homebrew_bin,
        )

        self.assertEqual(selected, homebrew_bin)

    def test_recommended_bin_dir_falls_back_to_user_local_without_path_mutation(self):
        home = self.tmp / "home"
        path_text = os.pathsep.join([str(self.tmp / "not-writable"), "/usr/bin"])

        selected = cli.recommended_bin_dir(
            platform_name="posix",
            path_text=path_text,
            home=home,
            is_writable=lambda _path: False,
        )

        self.assertEqual(selected, home / ".local" / "bin")

    def test_recommended_bin_dir_uses_windows_user_app_bin_fallback(self):
        home = PureWindowsPath("C:/Users/Ryan")

        selected = cli.recommended_bin_dir(
            platform_name="windows",
            path_text=r"C:\Windows\System32",
            home=home,
            environ={"LOCALAPPDATA": r"C:\Users\Ryan\AppData\Local"},
            is_writable=lambda _path: False,
        )

        self.assertEqual(selected, PureWindowsPath(r"C:\Users\Ryan\AppData\Local\Programs\auto-iteration\bin"))

    def test_stable_install_docs_avoid_single_platform_source_paths(self):
        stable_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "skills" / "auto-iteration-entry" / "SKILL.md",
            REPO_ROOT / "skills" / "auto-iteration" / "SKILL.md",
            REPO_ROOT / ".codex" / "hooks.json",
            REPO_ROOT / "auto_iteration" / "cli.py",
            REPO_ROOT / "plans" / "global_plan.md",
            REPO_ROOT / "plans" / "version_iterations.md",
            REPO_ROOT / "plans" / "active_plan.md",
        ]
        for path in stable_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/home/ryan/auto_iteration", text, str(path))
            self.assertNotIn("/Users/ryan/Documents/auto_continueous_dev", text, str(path))
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Windows Codex app", readme)
        self.assertIn("WSL/Linux Codex CLI", readme)
        self.assertIn("macOS Codex app", readme)

    def test_stop_hook_uses_default_cross_platform_handoff_command(self):
        hooks = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]

        self.assertEqual(command, "auto-iter handoff generate")
        self.assertNotIn("--quiet", command)
        self.assertNotIn(">", command)
        self.assertNotIn("2>", command)
        self.assertNotIn("&&", command)
        self.assertNotIn(";", command)

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
        self.assertIn(".auto_iter/: consolidated AIT project state directory", result.stdout)
        self.assertIn("project state preserved", result.stdout)
        self.assertFalse(command_path.exists())
        self.assertFalse(entry_skill_path.exists())
        self.assertFalse(improve_skill_path.exists())
        self.assertTrue((self.tmp / ".auto_iter" / "state" / "agent_state.db").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "plans" / "active_plan.md").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "raw_input").is_dir())

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
        self.assertIn(".auto_iter/: consolidated AIT project state directory", result.stdout)
        self.assertIn("removed project state: .auto_iter", result.stdout)
        self.assertFalse((self.tmp / ".auto_iter").exists())

    def test_update_replaces_installed_command_and_skills(self):
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        run_cli(self.tmp, "install", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))

        command_path = bin_dir / "auto-iter"
        expected_target = str(REPO_ROOT / "tools" / "auto_iter.py")
        command_path.write_text(f"stale wrapper for {expected_target}\n", encoding="utf-8")
        stale_skill_file = skills_dir / "auto-iteration-entry" / "STALE.txt"
        stale_skill_file.write_text("old skill artifact\n", encoding="utf-8")

        result = run_cli(self.tmp, "update", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))

        self.assertIn("removed command", result.stdout)
        self.assertIn("removed skill: auto-iteration-entry", result.stdout)
        self.assertIn("installed command", result.stdout)
        self.assertIn("installed skill", result.stdout)
        self.assertIn("update check: ok", result.stdout)
        self.assertTrue(command_path.exists())
        self.assertNotIn("stale wrapper", command_path.read_text(encoding="utf-8"))
        self.assertFalse(stale_skill_file.exists())

    def test_update_preserves_existing_project_state_directories(self):
        run_cli(self.tmp, "init")
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"
        state_root = self.tmp / ".auto_iter"
        for directory in ["state", "plans", "topics", "raw_input", "decisions", "runs", "handoffs"]:
            marker = state_root / directory / "update-marker.txt"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(f"keep {directory}\n", encoding="utf-8")

        result = run_cli(self.tmp, "update", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))

        self.assertIn("project state preserved", result.stdout)
        self.assertIn("update check: ok", result.stdout)
        for directory in ["state", "plans", "topics", "raw_input", "decisions", "runs", "handoffs"]:
            self.assertTrue((state_root / directory).is_dir())
            self.assertTrue((state_root / directory / "update-marker.txt").exists())

    def test_update_in_empty_directory_does_not_create_project_state(self):
        bin_dir = self.tmp / "bin"
        skills_dir = self.tmp / "skills"

        result = run_cli(self.tmp, "update", "--bin-dir", str(bin_dir), "--skills-dir", str(skills_dir))

        self.assertIn("update check: ok", result.stdout)
        for directory in ["state", "plans", "topics", "raw_input", "decisions", "runs", "handoffs"]:
            self.assertFalse((self.tmp / directory).exists(), directory)
        self.assertFalse((self.tmp / ".auto_iter").exists())

    def test_update_check_project_runs_doctor_or_skips_without_init(self):
        initialized = self.tmp / "initialized"
        empty = self.tmp / "empty"
        initialized.mkdir()
        empty.mkdir()
        run_cli(initialized, "init")

        initialized_result = run_cli(
            initialized,
            "update",
            "--bin-dir",
            str(initialized / "bin"),
            "--skills-dir",
            str(initialized / "skills"),
            "--check-project",
        )
        empty_result = run_cli(
            empty,
            "update",
            "--bin-dir",
            str(empty / "bin"),
            "--skills-dir",
            str(empty / "skills"),
            "--check-project",
        )

        self.assertIn("state: ok", initialized_result.stdout)
        self.assertIn("database: ok", initialized_result.stdout)
        self.assertIn("project check skipped", empty_result.stdout)
        self.assertFalse((empty / "state").exists())
        self.assertFalse((empty / "plans").exists())

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
        self.assertIn("第一个 topic 的摘要", (self.tmp / ".auto_iter" / "topics" / "active_topic.md").read_text(encoding="utf-8"))

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
        first_archive = self.tmp / ".auto_iter" / "topics" / "archive" / f"{first_topic_id}.md"

        self.assertIn("Topic A", listed.stdout)
        self.assertIn("archived_open", listed.stdout)
        self.assertIn("Topic B", listed.stdout)
        self.assertIn("active", listed.stdout)
        self.assertTrue(first_archive.exists())
        self.assertIn("Topic A 当前现场", first_archive.read_text(encoding="utf-8"))
        self.assertIn("Topic B", (self.tmp / ".auto_iter" / "topics" / "active_topic.md").read_text(encoding="utf-8"))

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
        self.assertIn("Topic B 当前现场", (self.tmp / ".auto_iter" / "topics" / "archive" / f"{second_topic_id}.md").read_text(encoding="utf-8"))

        satisfied = run_cli(self.tmp, "topic", "satisfy", "--summary", "Topic A 阶段性达到预期")
        no_current = run_cli(self.tmp, "topic", "current", check=False)

        self.assertIn(f"satisfied topic {first_topic_id}", satisfied.stdout)
        self.assertEqual(no_current.returncode, 1)
        self.assertIn("no active topic", no_current.stderr)
        self.assertIn("archived_satisfied", run_cli(self.tmp, "topic", "list").stdout)
        self.assertIn("Topic A 阶段性达到预期", first_archive.read_text(encoding="utf-8"))

        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
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
        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        skill_text = (skills_dir / "auto-iteration-entry" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("topics/index.md", index.stdout)
        self.assertIn("topics/active_topic.md", index.stdout)
        self.assertIn("Topic Archive MVP", index.stdout)
        self.assertEqual(handoff.stdout, "")
        self.assertIn("active_topic", handoff_text)
        self.assertIn(".auto_iter/topics/active_topic.md", handoff_text)
        self.assertIn("topic_index", handoff_text)
        self.assertIn(".auto_iter/topics/index.md", handoff_text)
        self.assertIn("topic_board", handoff_text)
        self.assertIn(".auto_iter/topics/board.md", handoff_text)
        self.assertIn("是不是已经切入新的 topic 了", skill_text)
        self.assertIn("auto-iter topic", skill_text)
        self.assertIn("install check: ok", installed.stdout)

    def test_topic_plan_set_show_current_and_context_index(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic Plan MVP",
            "--summary",
            "需要 topic 内计划",
        ).stdout.strip().split()[-1]

        saved = run_cli(
            self.tmp,
            "topic",
            "plan",
            "set",
            "--topic-id",
            topic_id,
            "--goal",
            "让当前 topic 有清晰验收",
            "--non-goal",
            "不替代 decision 结论",
            "--acceptance",
            "topic plan 能被 context index 找到",
            "--stop-condition",
            "验收项全部满足",
            "--escalation-condition",
            "影响多个 topic 时升级到 active_plan",
        )
        plan_path = self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md"
        default_plan_path = self.tmp / ".auto_iter" / "topics" / "default_topic_plan.md"

        self.assertIn(f"saved topic plan {topic_id}", saved.stdout)
        self.assertTrue(plan_path.exists())
        self.assertTrue(default_plan_path.exists())

        shown = run_cli(self.tmp, "topic", "plan", "show", "--topic-id", topic_id)
        current = run_cli(self.tmp, "topic", "plan", "current")
        index = run_cli(self.tmp, "context", "index")

        self.assertIn("让当前 topic 有清晰验收", shown.stdout)
        self.assertIn("不替代 decision 结论", shown.stdout)
        self.assertIn("影响多个 topic 时升级到 active_plan", current.stdout)
        self.assertIn(f"topics/{topic_id}/plan.md", index.stdout)
        self.assertIn("topics/default_topic_plan.md", index.stdout)

    def test_project_topic_links_are_queryable_from_both_sides_and_indexed(self):
        run_cli(self.tmp, "init")
        project_plan = self.tmp / ".auto_iter" / "plans" / "project_plan.md"
        project_plan.write_text("# Project Plan\n\n## ALN Landing\n\n长期项目方向\n", encoding="utf-8")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "ALN FR optimize",
            "--summary",
            "当前执行 topic",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_id, "--goal", "验证 ALN 落地边界")

        linked = run_cli(
            self.tmp,
            "project",
            "link-topic",
            "--project-heading",
            "ALN Landing",
            "--topic-id",
            topic_id,
            "--relation",
            "implements",
            "--summary",
            "该 topic 执行 ALN Landing 的落地验证",
        )
        project_links = run_cli(self.tmp, "project", "topic-links", "--project-heading", "ALN Landing")
        topic_links = run_cli(self.tmp, "topic", "project-links", "--topic-id", topic_id)
        index = run_cli(self.tmp, "context", "index")
        run_cli(self.tmp, "handoff", "generate")
        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        plan_text = (self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md").read_text(encoding="utf-8")
        board_text = (self.tmp / ".auto_iter" / "topics" / "board.md").read_text(encoding="utf-8")
        links_text = (self.tmp / ".auto_iter" / "plans" / "project_topic_links.md").read_text(encoding="utf-8")

        self.assertIn("linked project topic", linked.stdout)
        for text in [project_links.stdout, topic_links.stdout, handoff_text, plan_text, board_text, links_text]:
            self.assertIn("ALN Landing", text)
            self.assertIn(topic_id, text)
            self.assertIn("implements", text)
            self.assertIn("该 topic 执行 ALN Landing 的落地验证", text)
        self.assertIn("plans/project_topic_links.md", index.stdout)

    def test_topic_write_uses_environment_topic_id_and_reports_resolution(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Environment Topic",
            "--summary",
            "用环境变量指定 topic",
        ).stdout.strip().split()[-1]

        saved = run_cli(
            self.tmp,
            "topic",
            "plan",
            "set",
            "--goal",
            "环境变量指定 topic plan",
            env_extra={"AUTO_ITER_TOPIC_ID": topic_id},
        )
        added = run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--title",
            "环境变量指定 task",
            env_extra={"AUTO_ITER_TOPIC_ID": topic_id},
        )

        self.assertIn(f"resolved_topic_id: {topic_id}", saved.stdout)
        self.assertIn("resolved_topic_source: environment", saved.stdout)
        self.assertIn(f"resolved_topic_id: {topic_id}", added.stdout)
        self.assertIn("resolved_topic_source: environment", added.stdout)
        self.assertIn("环境变量指定 task", (self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md").read_text(encoding="utf-8"))

    def test_topic_write_rejects_implicit_default_when_multiple_topics_are_open(self):
        run_cli(self.tmp, "init")
        topic_a = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Open Topic A",
            "--summary",
            "第一个 open topic",
        ).stdout.strip().split()[-1]
        topic_b = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Open Topic B",
            "--summary",
            "第二个 open topic",
            "--current-summary",
            "Topic A 暂停",
        ).stdout.strip().split()[-1]

        blocked = run_cli(
            self.tmp,
            "topic",
            "plan",
            "set",
            "--goal",
            "不能隐式写入 default topic",
            check=False,
        )
        allowed = run_cli(
            self.tmp,
            "topic",
            "plan",
            "set",
            "--allow-default-topic",
            "--goal",
            "确认写入 default topic",
        )

        self.assertEqual(blocked.returncode, 1)
        self.assertIn("multiple open topics", blocked.stderr)
        self.assertIn("--topic-id", blocked.stderr)
        self.assertIn(f"resolved_topic_id: {topic_b}", allowed.stdout)
        self.assertIn("resolved_topic_source: default_topic", allowed.stdout)
        self.assertFalse((self.tmp / ".auto_iter" / "topics" / topic_a / "plan.md").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "topics" / topic_b / "plan.md").exists())

    def test_migrate_creates_empty_topic_plans_and_board_for_existing_topics(self):
        run_cli(self.tmp, "init")
        legacy_global_plan = self.tmp / ".auto_iter" / "plans" / "global_plan.md"
        legacy_global_plan.write_text("# Global Plan\n\n## Legacy Topic Routing\n\nold-route\n", encoding="utf-8")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Legacy Topic",
            "--summary",
            "旧 topic 没有 plan",
        ).stdout.strip().split()[-1]
        self.assertFalse((self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md").exists())

        migrated = run_cli(self.tmp, "migrate")

        plan_path = self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md"
        board_path = self.tmp / ".auto_iter" / "topics" / "board.md"
        migration_notes = list((self.tmp / ".auto_iter" / "topics").glob("migration_*_project_plan_split.md"))
        self.assertIn("migration complete", migrated.stdout)
        self.assertIn("created_topic_plans: 1", migrated.stdout)
        self.assertIn(f"default_topic_id: {topic_id}", migrated.stdout)
        self.assertTrue(plan_path.exists())
        self.assertTrue(board_path.exists())
        self.assertEqual(len(migration_notes), 1)
        self.assertIn(topic_id, migration_notes[0].read_text(encoding="utf-8"))
        self.assertIn("## Goal", plan_path.read_text(encoding="utf-8"))

    def test_migrate_splits_project_plan_without_losing_legacy_global_plan(self):
        run_cli(self.tmp, "init", "--legacy-layout")
        legacy_global_plan = self.tmp / "plans" / "global_plan.md"
        legacy_global_plan.write_text(
            "# Global Plan\n\n## Valeo Direction\n\nlegacy-valeo-project-route\n",
            encoding="utf-8",
        )
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Valeo RSPVis topic",
            "--summary",
            "旧 Valeo topic",
        ).stdout.strip().split()[-1]

        migrated = run_cli(self.tmp, "migrate")

        project_plan = self.tmp / "plans" / "project_plan.md"
        project_record_rules = self.tmp / "plans" / "project_record_rules.md"
        legacy_archive = self.tmp / "plans" / "legacy_global_plan_before_project_plan_split.md"
        compatibility_global_plan = self.tmp / "plans" / "global_plan.md"
        migration_notes = list((self.tmp / "topics").glob("migration_*_project_plan_split.md"))

        self.assertIn("project_plan", migrated.stdout)
        self.assertIn("project_record_rules", migrated.stdout)
        self.assertIn("legacy_global_plan", migrated.stdout)
        self.assertTrue(project_plan.exists())
        self.assertTrue(project_record_rules.exists())
        self.assertTrue(legacy_archive.exists())
        self.assertEqual(
            legacy_archive.read_text(encoding="utf-8"),
            "# Global Plan\n\n## Valeo Direction\n\nlegacy-valeo-project-route\n",
        )
        self.assertIn("compatibility entry", compatibility_global_plan.read_text(encoding="utf-8"))
        self.assertEqual(len(migration_notes), 1)
        migration_text = migration_notes[0].read_text(encoding="utf-8")
        self.assertIn(topic_id, migration_text)
        self.assertIn("legacy_global_plan_before_project_plan_split.md", migration_text)
        self.assertTrue((self.tmp / "topics" / topic_id / "plan.md").exists())
        migrated_again = run_cli(self.tmp, "migrate")
        self.assertEqual(len(list((self.tmp / "topics").glob("migration_*_project_plan_split.md"))), 1)
        self.assertIn(str(migration_notes[0].resolve()), migrated_again.stdout)

    def test_migrate_single_dir_layout_moves_legacy_state_without_losing_records(self):
        run_cli(self.tmp, "init", "--legacy-layout")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        raw_note = self.tmp / "raw_input" / "legacy.md"
        write_json(config, {"case": "single-dir-layout"})
        write_json(metrics, {"score": 1})
        artifact.write_text("# report\n\nsingle-dir-layout artifact\n", encoding="utf-8")
        raw_note.write_text("# Raw\n\nraw survives migration\n", encoding="utf-8")
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "migration-dataset",
            "--command",
            "python demo_task.py",
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
            "--title",
            "single dir migration keeps records",
            "--claim",
            "迁移后仍能读取 run 和 decision。",
            "--evidence",
            run_id,
        )

        result = run_cli(self.tmp, "migrate", "--layout", "single-dir")
        state_root = self.tmp / ".auto_iter"
        doctor = run_cli(self.tmp, "doctor")
        index = run_cli(self.tmp, "context", "index", "--include-raw-input")
        handoff = run_cli(self.tmp, "handoff", "generate", "--print-path")
        validated = run_cli(self.tmp, "handoff", "validate")

        self.assertIn("layout migration complete", result.stdout)
        self.assertTrue((state_root / "state" / "agent_state.db").exists())
        self.assertTrue((state_root / "runs" / run_id / "summary.md").exists())
        self.assertTrue((state_root / "raw_input" / "legacy.md").exists())
        self.assertFalse((self.tmp / "state").exists())
        self.assertFalse((self.tmp / "runs").exists())
        self.assertIn("layout: single-dir", doctor.stdout)
        self.assertIn(f"state_dir: {state_root}", doctor.stdout)
        self.assertIn(".auto_iter/plans/global_plan.md", index.stdout)
        self.assertIn(".auto_iter/raw_input/legacy.md", index.stdout)
        self.assertIn(str(state_root / "handoffs" / "latest_handoff.md"), handoff.stdout)
        self.assertIn("VALID", validated.stdout)

    def test_migrate_single_dir_layout_refuses_to_overwrite_existing_state_dir(self):
        run_cli(self.tmp, "init", "--legacy-layout")
        (self.tmp / ".auto_iter").mkdir()
        (self.tmp / ".auto_iter" / "marker.txt").write_text("existing state\n", encoding="utf-8")

        result = run_cli(self.tmp, "migrate", "--layout", "single-dir", check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn(".auto_iter already exists and is not empty", result.stderr)
        self.assertTrue((self.tmp / "state" / "agent_state.db").exists())

    def test_migrate_prints_follow_up_checklist_and_rule_backfill_hint(self):
        run_cli(self.tmp, "init")

        migrated = run_cli(self.tmp, "migrate")

        self.assertIn("rules_snapshot:", migrated.stdout)
        self.assertIn("rule_count: 0", migrated.stdout)
        self.assertIn("next_step_1: run `auto-iter doctor`", migrated.stdout)
        self.assertIn("next_step_2: review", migrated.stdout)
        self.assertIn("next_step_3: inspect", migrated.stdout)
        self.assertIn("rule_migration_hint:", migrated.stdout)
        self.assertIn("auto-iter rule add", migrated.stdout)

    def test_handoff_validate_warns_about_topic_without_plan_without_failing(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Legacy Topic Warning",
            "--summary",
            "旧 topic 没有 plan",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "handoff", "generate")

        validated = run_cli(self.tmp, "handoff", "validate")

        self.assertEqual(validated.returncode, 0)
        self.assertIn("VALID", validated.stdout)
        self.assertIn("WARNING", validated.stdout)
        self.assertIn(topic_id, validated.stdout)

    def test_topic_task_add_set_list_and_projection(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic Tasks",
            "--summary",
            "需要 topic 内任务状态",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_id, "--goal", "推进 topic tasks")

        added = run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_id,
            "--title",
            "写任务状态表",
            "--description",
            "保存 topic 内任务状态",
            "--acceptance",
            "plan projection 显示 doing",
        )
        item_id = added.stdout.strip().split()[-1]

        moved = run_cli(self.tmp, "topic", "task", "set", "--item-id", item_id, "--status", "doing")
        listed = run_cli(self.tmp, "topic", "task", "list", "--topic-id", topic_id)
        plan_text = (self.tmp / ".auto_iter" / "topics" / topic_id / "plan.md").read_text(encoding="utf-8")

        self.assertIn(f"added topic task {item_id}", added.stdout)
        self.assertIn(f"updated topic task {item_id}", moved.stdout)
        self.assertIn("doing", listed.stdout)
        self.assertIn("写任务状态表", listed.stdout)
        self.assertIn("## Doing", plan_text)
        self.assertIn("写任务状态表", plan_text)

    def test_topic_board_projects_cross_topic_task_state(self):
        run_cli(self.tmp, "init")
        topic_a = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Blocked Topic",
            "--summary",
            "需要 project board 显示 blocked",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_a, "--goal", "跟踪 blocked 任务")
        run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_a,
            "--status",
            "blocked",
            "--title",
            "等待外部结论",
        )
        topic_b = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Ready Topic",
            "--summary",
            "没有未完成任务",
            "--current-summary",
            "Blocked topic 暂停",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_b, "--goal", "可满足 topic")
        done_item = run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_b,
            "--status",
            "done",
            "--title",
            "已完成验收",
        ).stdout.strip().split()[-1]

        board = run_cli(self.tmp, "topic", "board")

        board_path = self.tmp / ".auto_iter" / "topics" / "board.md"
        self.assertTrue(board_path.exists())
        self.assertIn("# Project Topic Board", board.stdout)
        self.assertIn("## Open Topics", board.stdout)
        self.assertIn("## Blocked Tasks", board.stdout)
        self.assertIn("等待外部结论", board.stdout)
        self.assertIn("## Recent Done Tasks", board.stdout)
        self.assertIn(done_item, board.stdout)
        self.assertIn("## Ready To Satisfy", board.stdout)
        self.assertIn(topic_b, board.stdout)
        self.assertEqual(board.stdout, board_path.read_text(encoding="utf-8"))

    def test_topic_handoff_board_and_plan_are_indexed_for_search(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Search Topic",
            "--summary",
            "v028_search_anchor topic summary",
        ).stdout.strip().split()[-1]
        run_cli(
            self.tmp,
            "topic",
            "plan",
            "set",
            "--topic-id",
            topic_id,
            "--goal",
            "v028_search_anchor plan goal",
        )
        run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_id,
            "--status",
            "doing",
            "--title",
            "v028_search_anchor task",
        )
        run_cli(self.tmp, "handoff", "generate", "--topic-id", topic_id)
        run_cli(self.tmp, "topic", "board")

        index = run_cli(self.tmp, "context", "index")
        search_index = run_cli(self.tmp, "search", "index")
        query = run_cli(self.tmp, "search", "query", "--text", "v028_search_anchor", "--limit", "5", "--explain")

        topic_plan = f".auto_iter/topics/{topic_id}/plan.md"
        topic_handoff = f".auto_iter/topics/{topic_id}/latest_handoff.md"
        topic_board = ".auto_iter/topics/board.md"
        self.assertIn(topic_plan, index.stdout)
        self.assertIn(topic_handoff, index.stdout)
        self.assertIn(topic_board, index.stdout)
        self.assertIn("indexed graph edges:", search_index.stdout)
        self.assertIn("v028_search_anchor", query.stdout)
        self.assertIn(topic_id, query.stdout)
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            rows = db.execute(
                """
                select source_type, source_id, path
                from search_documents
                where path in (?, ?, ?)
                """,
                (topic_plan, topic_handoff, topic_board),
            ).fetchall()
            source_types = {row[2]: (row[0], row[1]) for row in rows}
            edge_count = db.execute(
                """
                select count(*)
                from search_graph_edges
                join search_documents source on source.doc_id = search_graph_edges.source_doc_id
                join search_documents target on target.doc_id = search_graph_edges.target_doc_id
                where source.path = ? and target.path = ?
                """,
                (topic_plan, topic_handoff),
            ).fetchone()[0]
        self.assertEqual(source_types[topic_plan], ("topic_plan", topic_id))
        self.assertEqual(source_types[topic_handoff], ("topic_handoff", topic_id))
        self.assertEqual(source_types[topic_board], ("topic_board", "board"))
        self.assertGreater(edge_count, 0)

    def test_search_index_handles_repeated_headings_in_one_file(self):
        run_cli(self.tmp, "init")
        repeated = self.tmp / ".auto_iter" / "plans" / "repeated_headings.md"
        repeated.write_text(
            "# Same Heading\n"
            "first v029_duplicate_heading_anchor\n\n"
            "# Same Heading\n"
            "second v029_duplicate_heading_anchor\n",
            encoding="utf-8",
        )

        result = run_cli(self.tmp, "search", "index")

        self.assertIn("indexed search documents:", result.stdout)
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            rows = db.execute(
                """
                select doc_id, heading, body
                from search_documents
                where path = ?
                order by body
                """,
                (".auto_iter/plans/repeated_headings.md",),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0][0], rows[1][0])
        self.assertEqual({row[1] for row in rows}, {"Same Heading"})

    def test_search_query_reuses_fresh_index(self):
        run_cli(self.tmp, "init")
        anchor = self.tmp / ".auto_iter" / "plans" / "search_reuse.md"
        anchor.write_text("# Search Reuse\nv030_reuse_anchor\n", encoding="utf-8")

        first = run_cli(self.tmp, "search", "query", "--text", "v030_reuse_anchor", "--limit", "5")
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            first_updated_at = db.execute(
                "select updated_at from search_documents where path = ?",
                (".auto_iter/plans/search_reuse.md",),
            ).fetchone()[0]

        second = run_cli(self.tmp, "search", "query", "--text", "v030_reuse_anchor", "--limit", "5")

        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            second_updated_at = db.execute(
                "select updated_at from search_documents where path = ?",
                (".auto_iter/plans/search_reuse.md",),
            ).fetchone()[0]
        self.assertIn("v030_reuse_anchor", first.stdout)
        self.assertIn("v030_reuse_anchor", second.stdout)
        self.assertEqual(first_updated_at, second_updated_at)

    def test_search_query_refreshes_when_index_input_changes(self):
        run_cli(self.tmp, "init")
        first_anchor = self.tmp / ".auto_iter" / "plans" / "search_refresh_a.md"
        first_anchor.write_text("# Search Refresh A\nv030_refresh_a\n", encoding="utf-8")
        run_cli(self.tmp, "search", "query", "--text", "v030_refresh_a", "--limit", "5")

        second_anchor = self.tmp / ".auto_iter" / "plans" / "search_refresh_b.md"
        second_anchor.write_text("# Search Refresh B\nv030_refresh_b\n", encoding="utf-8")
        refreshed = run_cli(self.tmp, "search", "query", "--text", "v030_refresh_b", "--limit", "5")

        self.assertIn("v030_refresh_b", refreshed.stdout)

    def test_search_query_uses_stale_index_when_refresh_is_locked(self):
        run_cli(self.tmp, "init")
        first_anchor = self.tmp / ".auto_iter" / "plans" / "search_stale_a.md"
        first_anchor.write_text("# Search Stale A\nv030_stale_a\n", encoding="utf-8")
        run_cli(self.tmp, "search", "query", "--text", "v030_stale_a", "--limit", "5")
        second_anchor = self.tmp / ".auto_iter" / "plans" / "search_stale_b.md"
        second_anchor.write_text("# Search Stale B\nv030_stale_b\n", encoding="utf-8")
        (self.tmp / ".auto_iter" / "state" / "search_index.lock").mkdir()

        stale = run_cli(self.tmp, "search", "query", "--text", "v030_stale_a", "--limit", "5")

        self.assertIn("v030_stale_a", stale.stdout)
        self.assertIn("warning: search index refresh is already running", stale.stdout)

    def test_topic_evidence_links_runs_decisions_and_artifacts(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Evidence linked topic",
            "--summary",
            "需要能查到相关 run、decision 和 artifact",
        ).stdout.strip().split()[-1]
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        write_json(config, {"route": "topic-evidence"})
        write_json(metrics, {"score": 0.88})
        artifact.write_text("# linked report\n", encoding="utf-8")
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "topic-evidence",
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
        decision_id = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "Evidence link decision",
            "--claim",
            "topic 可以直接关联相关结论。",
        ).stdout.strip().split()[-1]
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            artifact_id = db.execute("select artifact_id from artifacts where run_id = ?", (run_id,)).fetchone()[0]

        linked = run_cli(
            self.tmp,
            "topic",
            "link",
            "--topic-id",
            topic_id,
            "--run-id",
            run_id,
            "--decision-id",
            decision_id,
            "--artifact-id",
            artifact_id,
            "--summary",
            "v0.16 evidence bundle",
        )
        evidence = run_cli(self.tmp, "topic", "evidence", "--topic-id", topic_id)
        current = run_cli(self.tmp, "topic", "current")
        index = run_cli(self.tmp, "context", "index")
        handoff = run_cli(self.tmp, "handoff", "generate")
        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")

        self.assertIn("linked topic evidence", linked.stdout)
        self.assertIn(run_id, evidence.stdout)
        self.assertIn(decision_id, evidence.stdout)
        self.assertIn(artifact_id, evidence.stdout)
        self.assertIn("v0.16 evidence bundle", evidence.stdout)
        self.assertIn("## Evidence Links", current.stdout)
        self.assertIn(run_id, current.stdout)
        self.assertIn("Evidence Links", index.stdout)
        self.assertIn("## Topic Evidence Links", handoff_text)
        self.assertIn(run_id, handoff_text)
        self.assertEqual(handoff.stdout, "")

        missing = run_cli(
            self.tmp,
            "topic",
            "link",
            "--topic-id",
            topic_id,
            "--run-id",
            "R-missing",
            check=False,
        )
        self.assertEqual(missing.returncode, 1)
        self.assertIn("unknown run evidence_id: R-missing", missing.stderr)

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
        self.assertIn("plot.txt", shown.stdout)
        self.assertNotIn(str(artifact.resolve()), shown.stdout)

        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            metric = db.execute(
                "select metric_value, unit, direction from metrics where run_id = ? and metric_name = ?",
                (run_id, "precision"),
            ).fetchone()
        self.assertEqual(metric, (0.91, "ratio", "higher_is_better"))
        self.assertTrue((self.tmp / ".auto_iter" / "runs" / run_id / "summary.md").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "runs" / run_id / "logs" / "error_summary.md").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "runs" / run_id / "logs" / "stdout.log").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "runs" / run_id / "logs" / "stderr.log").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "runs" / run_id / "logs" / "debug.jsonl").exists())

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
        run_dir = self.tmp / ".auto_iter" / "runs" / run_id

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
        run_dir = self.tmp / ".auto_iter" / "runs" / run_id

        self.assertEqual(result.returncode, 3)
        self.assertIn("status=failed", result.stdout)
        self.assertIn("fatal detail", (run_dir / "logs" / "stderr.log").read_text(encoding="utf-8"))
        self.assertIn("fatal detail", (run_dir / "logs" / "error_summary.md").read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
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

        handoff = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("global_plan", handoff)
        self.assertIn("v0.2 入口流程演示通过", handoff)
        self.assertIn("entry flow complete", (self.tmp / ".auto_iter" / "runs" / run_id / "logs" / "stdout.log").read_text(encoding="utf-8"))

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

        decision_id = run_cli(
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

        decision_id = run_cli(
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

        self.assertEqual(valid.stdout, "")
        validated = run_cli(self.tmp, "handoff", "validate")
        self.assertIn("VALID", validated.stdout)

        handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        text = handoff_path.read_text(encoding="utf-8").replace("## 读取顺序", "## Broken Read Order")
        handoff_path.write_text(text, encoding="utf-8")
        invalid = run_cli(self.tmp, "handoff", "validate", check=False)

        self.assertEqual(invalid.returncode, 1)
        self.assertIn("INVALID", invalid.stdout)
        self.assertIn("missing section: ## 读取顺序", invalid.stdout)

    def test_context_index_and_handoff_validate_flag_orphan_decision_projections(self):
        run_cli(self.tmp, "init")
        orphan = self.tmp / ".auto_iter" / "decisions" / "active" / "D-orphan.md"
        orphan.write_text(
            "# 演示测试结论\n\n"
            "- decision_id: D-orphan\n"
            "- status: active\n"
            "- evidence_run_ids: R-missing\n\n"
            "## 结论\n"
            "这是测试数据，不应被当成当前项目结论。\n",
            encoding="utf-8",
        )
        config = self.tmp / "config.json"
        write_json(config, {"kind": "real-context"})
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "real-context",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        decision_id = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "真实账本结论",
            "--claim",
            "这个结论存在于 SQLite，因此可以进入上下文索引。",
        ).stdout.strip().split()[-1]
        stale = self.tmp / ".auto_iter" / "decisions" / "rejected" / f"{decision_id}.md"
        stale.write_text(
            "# 状态错误的投影\n\n"
            f"- decision_id: {decision_id}\n"
            "- status: rejected\n"
            f"- evidence_run_ids: {run_id}\n\n"
            "## 结论\n"
            "这个 projection 的目录状态和 SQLite 不一致。\n",
            encoding="utf-8",
        )
        run_cli(self.tmp, "handoff", "generate")

        index = run_cli(self.tmp, "context", "index")
        validated = run_cli(self.tmp, "handoff", "validate", check=False)

        self.assertNotIn("# 演示测试结论", index.stdout)
        self.assertIn("# 真实账本结论", index.stdout)
        self.assertIn("orphan decision projection skipped", index.stdout)
        self.assertIn("stale decision projection skipped", index.stdout)
        self.assertEqual(validated.returncode, 1)
        self.assertIn("INVALID", validated.stdout)
        self.assertIn("orphan decision projection", validated.stdout)
        self.assertIn("stale decision projection", validated.stdout)

    def test_context_index_and_show_exclude_raw_input_by_default(self):
        run_cli(self.tmp, "init")
        raw_note = self.tmp / ".auto_iter" / "raw_input" / "legacy.md"
        raw_archive = self.tmp / ".auto_iter" / "raw_input" / "legacy.mhtml"
        raw_note.write_text("# Legacy Raw Input\n\nlegacy-only detail\n", encoding="utf-8")
        raw_archive.write_text("<html><body>archived source detail</body></html>\n", encoding="utf-8")

        index = run_cli(self.tmp, "context", "index")
        raw_index = run_cli(self.tmp, "context", "index", "--include-raw-input")
        shown = run_cli(
            self.tmp,
            "context",
            "show",
            "--path",
            str(self.tmp / ".auto_iter" / "plans" / "global_plan.md"),
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

    def test_search_index_and_query_find_decision_without_raw_input(self):
        run_cli(self.tmp, "init")
        raw_note = self.tmp / ".auto_iter" / "raw_input" / "legacy.md"
        raw_note.write_text("# Legacy Raw Input\n\nraw-only-secret-phenomenon\n", encoding="utf-8")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        write_json(config, {"case": "front-radar-static-jump"})
        write_json(metrics, {"yaw_p95_p05": {"value": 0.42, "unit": "deg", "direction": "minimize"}})
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "front-radar",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "run", "finish", run_id, "--status", "success", "--metrics", str(metrics))
        decision_id = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "前雷达静态点跳变现象",
            "--claim",
            "之前确认过 front radar 的静态点跳变现象，应该从证据 run 继续查。",
        ).stdout.strip().split()[-1]

        indexed = run_cli(self.tmp, "search", "index")
        queried = run_cli(
            self.tmp,
            "search",
            "query",
            "--text",
            "我记得之前说过 front radar 静态点跳变",
            "--limit",
            "5",
            "--explain",
        )

        self.assertIn("indexed search documents", indexed.stdout)
        self.assertIn("前雷达静态点跳变现象", queried.stdout)
        self.assertIn(decision_id, queried.stdout)
        self.assertIn(run_id, queried.stdout)
        self.assertIn("bm25", queried.stdout)
        self.assertIn("light_vector", queried.stdout)
        self.assertIn("context show", queried.stdout)
        self.assertNotIn("raw-only-secret-phenomenon", queried.stdout)

    def test_search_query_expands_structured_evidence_links(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        write_json(config, {"case": "evidence-link"})
        write_json(metrics, {"score": {"value": 1.0, "unit": "ratio", "direction": "maximize"}})
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "linked-run-dataset",
            "--command",
            "python experiment.py",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "run", "finish", run_id, "--status", "success", "--metrics", str(metrics))
        decision_id = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "linked evidence conclusion",
            "--claim",
            "unique linked phenomenon lives in the decision, not in the run summary.",
        ).stdout.strip().split()[-1]

        run_cli(self.tmp, "search", "index")
        queried = run_cli(
            self.tmp,
            "search",
            "query",
            "--text",
            "unique linked phenomenon",
            "--limit",
            "8",
            "--explain",
        )

        self.assertIn(decision_id, queried.stdout)
        self.assertIn(run_id, queried.stdout)
        self.assertIn("graph", queried.stdout)
        self.assertIn("source=run", queried.stdout)

    def test_run_import_records_external_rejected_experiment_summary_for_decision_evidence(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "bucket_config.json"
        metrics = self.tmp / "bucket_metrics.json"
        artifact = self.tmp / "bucket_report.md"
        write_json(config, {"bucket_size_mps": 0.005, "case": "aln-residual-bucket"})
        write_json(metrics, {"fc_valid_flips": 97, "fr_valid_delta": 18})
        artifact.write_text("final LSQ point list changed\n", encoding="utf-8")

        imported = run_cli(
            self.tmp,
            "run",
            "import",
            "--config",
            str(config),
            "--dataset",
            "external-sil",
            "--status",
            "failed",
            "--summary",
            "0.005m/s 分桶不等价，final LSQ 点列表变化，不能继续按该路线优化。",
            "--command",
            "external Codex session 019e6926-af2c-77e0-8666-f7d1f7dd5093",
            "--metrics",
            str(metrics),
            "--artifact",
            str(artifact),
            "--session",
            "019e6926-af2c-77e0-8666-f7d1f7dd5093",
        )
        run_id = imported.stdout.strip().split()[-1]

        self.assertRegex(imported.stdout, r"imported run R-[0-9a-f]+")
        summary_text = (self.tmp / ".auto_iter" / "runs" / run_id / "summary.md").read_text(encoding="utf-8")
        self.assertIn("## Summary", summary_text)
        self.assertIn("0.005m/s 分桶不等价", summary_text)
        self.assertIn("external Codex session 019e6926-af2c-77e0-8666-f7d1f7dd5093", summary_text)
        shown = run_cli(self.tmp, "run", "show", run_id)
        shown_json = json.loads(shown.stdout)
        self.assertEqual(shown_json["status"], "failed")
        self.assertIn("final LSQ 点列表变化", shown_json["summary"])

        decision = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "rejected",
            "--evidence",
            run_id,
            "--title",
            "拒绝 0.005m/s 分桶残差路线",
            "--claim",
            "0.005m/s 分桶导致 final LSQ 点列表变化，FC valid 翻转数量不可接受。",
            "--route-keyword",
            "分桶",
            "--route-keyword",
            "0.005m/s",
            "--reopen-condition",
            "只有 SIL KPI 证明 final LSQ 点列表变化被消除且 yaw 差异低于 0.1deg 时才允许重开。",
        )
        decision_id = decision.stdout.strip().split()[-1]
        decision_text = (
            self.tmp / ".auto_iter" / "decisions" / "rejected" / f"{decision_id}.md"
        ).read_text(encoding="utf-8")
        self.assertIn(run_id, decision_text)
        self.assertIn("0.005m/s", decision_text)

    def test_intent_check_flags_rejected_experiment_result_recording(self):
        run_cli(self.tmp, "init")

        result = run_cli(
            self.tmp,
            "intent",
            "check",
            "--text",
            "0.005m/s 分桶实验不等价，FC valid 翻转，不能合入。",
        )

        self.assertIn("intent: rejected-result-recording", result.stdout)
        self.assertIn("auto-iter run import", result.stdout)
        self.assertIn("auto-iter decision add --status rejected", result.stdout)
        self.assertIn("route-keyword", result.stdout)
        self.assertIn("reopen-condition", result.stdout)
        self.assertIn("auto-iter topic link", result.stdout)

    def test_checkpoint_save_warns_about_rejected_result_recording_debt(self):
        run_cli(self.tmp, "init")

        result = run_cli(
            self.tmp,
            "checkpoint",
            "save",
            "--text",
            "0.005m/s 分桶实验不等价，不能合入。",
        )

        self.assertIn("recording_debt_warning", result.stdout)
        self.assertIn("auto-iter run import", result.stdout)
        self.assertIn("auto-iter decision add --status rejected", result.stdout)

    def test_intent_check_suggests_safe_checkpoints_without_writing_state(self):
        run_cli(self.tmp, "init")

        before_execution = run_cli(self.tmp, "intent", "check", "--text", "确定执行，先跑实验")
        after_result = run_cli(self.tmp, "intent", "check", "--text", "拿到结果了，测试结束了")
        mid_session_record = run_cli(self.tmp, "intent", "check", "--text", "中途记录一下当前状态")
        adopted_plan = run_cli(
            self.tmp,
            "intent",
            "check",
            "--text",
            "方案是增加导出模式，下一步实现配置切换，并补充验收测试",
        )
        session_end_with_next_plan = run_cli(
            self.tmp,
            "intent",
            "check",
            "--text",
            "准备关 session，然后新 session 实施这个开发",
        )
        ait_self_iteration = run_cli(
            self.tmp,
            "intent",
            "check",
            "--text",
            "在 Valeo 目录里改 AIT update 和 auto-iter migrate 的计划",
        )

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
        self.assertIn("intent: topic-plan-carryover", adopted_plan.stdout)
        self.assertIn("persist it in the topic plan immediately", adopted_plan.stdout)
        self.assertIn("auto-iter topic plan set", adopted_plan.stdout)
        self.assertIn("auto-iter topic task add", adopted_plan.stdout)
        self.assertIn("before checkpoint or handoff", adopted_plan.stdout)
        self.assertIn("intent: session-end-implementation-carryover", session_end_with_next_plan.stdout)
        self.assertIn("auto-iter topic plan set", session_end_with_next_plan.stdout)
        self.assertIn("auto-iter topic task add", session_end_with_next_plan.stdout)
        self.assertIn("before handoff generate", session_end_with_next_plan.stdout)
        self.assertIn("intent: ownership-routing", ait_self_iteration.stdout)
        self.assertIn("If the request is about AIT itself", ait_self_iteration.stdout)
        self.assertIn("auto_iteration source repository", ait_self_iteration.stdout)
        self.assertIn("Do not write AIT tool work into the managed project's project plan or topic plan", ait_self_iteration.stdout)

    def test_checkpoint_save_generates_valid_handoff_without_commit_push(self):
        run_cli(self.tmp, "init")

        checkpoint = run_cli(self.tmp, "checkpoint", "save", "--text", "中途记录一下当前状态")

        handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        self.assertIn("CHECKPOINT SAVED", checkpoint.stdout)
        self.assertIn("handoff_valid: yes", checkpoint.stdout)
        self.assertIn("commit_push: not requested", checkpoint.stdout)
        self.assertIn(str(handoff_path.resolve()), checkpoint.stdout)
        self.assertTrue(handoff_path.exists())
        self.assertIn("## 当前快照", handoff_path.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            count = db.execute("select count(*) from handoffs").fetchone()[0]
        self.assertEqual(count, 1)

    def test_handoff_generate_topic_id_writes_topic_handoff_without_global_overwrite(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic Handoff",
            "--summary",
            "需要 topic 级交接",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_id, "--goal", "生成 topic 独立 handoff")
        run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_id,
            "--status",
            "doing",
            "--title",
            "写 topic handoff",
        )

        quiet = run_cli(self.tmp, "handoff", "generate", "--topic-id", topic_id)

        topic_handoff_path = self.tmp / ".auto_iter" / "topics" / topic_id / "latest_handoff.md"
        global_handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        self.assertEqual(quiet.stdout, "")
        self.assertEqual(quiet.stderr, "")
        self.assertTrue(topic_handoff_path.exists())
        self.assertFalse(global_handoff_path.exists())
        topic_handoff = topic_handoff_path.read_text(encoding="utf-8")
        self.assertIn("# Topic Handoff", topic_handoff)
        self.assertIn(f"- topic_id: {topic_id}", topic_handoff)
        self.assertIn("## Topic Plan", topic_handoff)
        self.assertIn("生成 topic 独立 handoff", topic_handoff)
        self.assertIn("## Topic Tasks", topic_handoff)
        self.assertIn("写 topic handoff", topic_handoff)

        validated = run_cli(self.tmp, "handoff", "validate", "--topic-id", topic_id)
        self.assertIn("VALID", validated.stdout)
        self.assertIn(str(topic_handoff_path.resolve()), validated.stdout)
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            rows = db.execute("select path from handoffs").fetchall()
        self.assertEqual([row[0] for row in rows], [str(topic_handoff_path.resolve())])

    def test_checkpoint_save_topic_id_generates_valid_topic_handoff(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Topic Checkpoint",
            "--summary",
            "需要 topic 级中途记录",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_id, "--goal", "保存 topic checkpoint")

        checkpoint = run_cli(
            self.tmp,
            "checkpoint",
            "save",
            "--topic-id",
            topic_id,
            "--text",
            "中途记录一下 topic 状态",
        )

        topic_handoff_path = self.tmp / ".auto_iter" / "topics" / topic_id / "latest_handoff.md"
        self.assertIn("CHECKPOINT SAVED", checkpoint.stdout)
        self.assertIn("handoff_valid: yes", checkpoint.stdout)
        self.assertIn(str(topic_handoff_path.resolve()), checkpoint.stdout)
        self.assertTrue(topic_handoff_path.exists())
        self.assertFalse((self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").exists())
        self.assertIn("保存 topic checkpoint", topic_handoff_path.read_text(encoding="utf-8"))

    def test_project_handoff_includes_topic_summary(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "Project Topic Summary",
            "--summary",
            "项目级 handoff 需要 topic 摘要",
        ).stdout.strip().split()[-1]
        run_cli(self.tmp, "topic", "plan", "set", "--topic-id", topic_id, "--goal", "展示 topic 总览")
        run_cli(
            self.tmp,
            "topic",
            "task",
            "add",
            "--topic-id",
            topic_id,
            "--status",
            "blocked",
            "--title",
            "等待 topic 证据",
        )

        run_cli(self.tmp, "handoff", "generate")

        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("## Topic Summary", handoff_text)
        self.assertIn("### Default Topic", handoff_text)
        self.assertIn("### Open Topics", handoff_text)
        self.assertIn("### Blocked Topic Tasks", handoff_text)
        self.assertIn(topic_id, handoff_text)
        self.assertIn("等待 topic 证据", handoff_text)

    def test_handoff_generate_writes_handoff_without_stdout_for_stop_hook(self):
        run_cli(self.tmp, "init")

        quiet = run_cli(self.tmp, "handoff", "generate")

        handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        self.assertEqual(quiet.stdout, "")
        self.assertEqual(quiet.stderr, "")
        self.assertTrue(handoff_path.exists())
        self.assertIn("## 当前快照", handoff_path.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            count = db.execute("select count(*) from handoffs").fetchone()[0]
        self.assertEqual(count, 1)

    def test_handoff_generate_print_path_is_explicit_debug_output(self):
        run_cli(self.tmp, "init")

        result = run_cli(self.tmp, "handoff", "generate", "--print-path")

        handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        self.assertIn(str(handoff_path.resolve()), result.stdout)
        self.assertIn("generated", result.stdout)

    def test_handoff_read_order_omits_missing_project_agents_file(self):
        run_cli(self.tmp, "init")

        run_cli(self.tmp, "handoff", "generate")

        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("## 读取顺序", handoff_text)
        self.assertNotIn(str(self.tmp / "AGENTS.md"), handoff_text)
        self.assertIn("1. .auto_iter/handoffs/latest_handoff.md", handoff_text)

    def test_handoff_read_order_includes_existing_project_agents_file(self):
        run_cli(self.tmp, "init")
        (self.tmp / "AGENTS.md").write_text("# Project Rules\n", encoding="utf-8")

        run_cli(self.tmp, "handoff", "generate")

        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("1. AGENTS.md", handoff_text)
        self.assertIn("2. .auto_iter/handoffs/latest_handoff.md", handoff_text)

    def test_handoff_uses_relative_project_paths_for_recovery_entries(self):
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

        handoff_path = self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md"
        text = handoff_path.read_text(encoding="utf-8")
        self.assertEqual(handoff.stdout, "")
        self.assertIn("## 当前目标", text)
        self.assertIn("project_plan", text)
        self.assertIn(".auto_iter/plans/project_plan.md", text)
        self.assertIn("project_record_rules", text)
        self.assertIn(".auto_iter/plans/project_record_rules.md", text)
        self.assertIn("global_plan_compat", text)
        self.assertIn(".auto_iter/plans/global_plan.md", text)
        self.assertIn("version_task_tracking", text)
        self.assertIn(".auto_iter/plans/version_iterations.md", text)
        self.assertIn("## 当前有效结论", text)
        self.assertIn("雨天阈值使用 0.58", text)
        self.assertIn("report.md", text)
        self.assertNotIn(str(artifact.resolve()), text)
        self.assertIn(str(handoff_path.resolve()), resume.stdout)

    def test_handoff_includes_current_baseline_projection(self):
        run_cli(self.tmp, "init")
        topic_id = run_cli(
            self.tmp,
            "topic",
            "start",
            "--title",
            "ALN bad-frame follow-up",
            "--summary",
            "继续验证 final LSQ 选点边界",
        ).stdout.strip().split()[-1]
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "diagnostic.md"
        write_json(config, {"postprocess_version": 8, "gate": "valid_yaw_measurement"})
        write_json(metrics, {"yaw_p95_p05_deg": {"value": 0.605269, "unit": "deg", "direction": "lower"}})
        artifact.write_text("# diagnostic evidence\n", encoding="utf-8")
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "fr-split-demo",
            "--command",
            "python aln_postprocess.py",
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
        decision_id = run_cli(
            self.tmp,
            "decision",
            "add",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--title",
            "V8 remains the current SIL alignment reference",
            "--claim",
            "Use V8 as the accepted comparison start; keep FR split evaluation and do not treat Python-only output as C/SIL landing.",
        ).stdout.strip().split()[-1]
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            artifact_id = db.execute("select artifact_id from artifacts where run_id = ?", (run_id,)).fetchone()[0]
        run_cli(
            self.tmp,
            "topic",
            "link",
            "--topic-id",
            topic_id,
            "--run-id",
            run_id,
            "--decision-id",
            decision_id,
            "--artifact-id",
            artifact_id,
            "--summary",
            "baseline, evaluation, provenance, and diagnostic entries",
        )

        run_cli(self.tmp, "handoff", "generate")

        handoff_text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn("## Current Baseline", handoff_text)
        self.assertIn(f"accepted_start: decision {decision_id}: V8 remains the current SIL alignment reference", handoff_text)
        self.assertIn(f"accepted_result: run {run_id}: dataset=fr-split-demo status=success", handoff_text)
        self.assertIn("why_current: Use V8 as the accepted comparison start", handoff_text)
        self.assertIn(
            f"evaluation_entry: .auto_iter/decisions/active/{decision_id}.md",
            handoff_text,
        )
        self.assertIn(
            f"provenance_entry: .auto_iter/runs/{run_id}/config_resolved.json",
            handoff_text,
        )
        self.assertIn("diagnostic_entry: diagnostic.md", handoff_text)

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
        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            db.execute("update runs set ended_at = '2026-01-01T00:00:00+00:00'")
            db.commit()

        run_cli(self.tmp, "handoff", "generate")

        text = (self.tmp / ".auto_iter" / "handoffs" / "latest_handoff.md").read_text(encoding="utf-8")
        self.assertIn(f"latest_successful_run_id: {second_run}", text)

    def test_rule_add_list_show_and_projection(self):
        run_cli(self.tmp, "init")
        config = self.tmp / "config.json"
        metrics = self.tmp / "metrics.json"
        artifact = self.tmp / "report.md"
        write_json(config, {"phase": "entry"})
        write_json(metrics, {"score": 1.0})
        artifact.write_text("# report\n", encoding="utf-8")
        run_id = run_cli(
            self.tmp,
            "run",
            "start",
            "--config",
            str(config),
            "--dataset",
            "rule-demo",
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

        added = run_cli(
            self.tmp,
            "rule",
            "add",
            "--title",
            "进入执行前必须先做 route check",
            "--claim",
            "任何实验执行前都先运行 route check，避免重复路线直接落库。",
            "--source-kind",
            "user_stated",
            "--rule-kind",
            "entry",
            "--scope-kind",
            "project",
            "--status",
            "active",
            "--evidence",
            run_id,
            "--evidence",
            f"path:{artifact}",
            "--note",
            "来自用户明确要求",
            "--note",
            "当前先用于通用 AIT 项目",
        )
        rule_id = added.stdout.strip().split()[-1]

        listed = run_cli(self.tmp, "rule", "list")
        shown = run_cli(self.tmp, "rule", "show", rule_id)

        projection = self.tmp / ".auto_iter" / "rules" / "active" / f"{rule_id}.md"
        snapshot = self.tmp / ".auto_iter" / "rules" / "current_effective.md"
        self.assertTrue(projection.exists())
        self.assertTrue(snapshot.exists())
        self.assertIn(rule_id, listed.stdout)
        self.assertIn("进入执行前必须先做 route check", listed.stdout)
        self.assertIn("source_kind=user_stated", listed.stdout)
        self.assertIn("scope_kind=project", listed.stdout)
        self.assertIn(f'"rule_id": "{rule_id}"', shown.stdout)
        self.assertIn("任何实验执行前都先运行 route check", shown.stdout)
        self.assertIn("来自用户明确要求", shown.stdout)
        self.assertIn(run_id, shown.stdout)
        self.assertIn("path", shown.stdout)
        self.assertIn("进入执行前必须先做 route check", projection.read_text(encoding="utf-8"))
        self.assertIn(rule_id, snapshot.read_text(encoding="utf-8"))

        with closing(sqlite3.connect(self.tmp / ".auto_iter" / "state" / "agent_state.db")) as db:
            row = db.execute(
                "select source_kind, rule_kind, scope_kind, status, evidence_json from rules where rule_id = ?",
                (rule_id,),
            ).fetchone()
        self.assertEqual("user_stated", row[0])
        self.assertEqual("entry", row[1])
        self.assertEqual("project", row[2])
        self.assertEqual("active", row[3])
        evidence_json = json.loads(row[4])
        self.assertEqual("run", evidence_json["items"][0]["kind"])
        self.assertEqual(run_id, evidence_json["items"][0]["value"])
        self.assertIn("来自用户明确要求", evidence_json["notes"])

    def test_rule_supersede_updates_context_index_and_effective_snapshot(self):
        run_cli(self.tmp, "init")
        first = run_cli(
            self.tmp,
            "rule",
            "add",
            "--title",
            "阶段记录默认不提交",
            "--claim",
            "中途 checkpoint 默认只记录当前状态，不提交不推送。",
            "--source-kind",
            "derived",
            "--rule-kind",
            "recording",
            "--scope-kind",
            "global",
            "--status",
            "active",
            "--note",
            "来自现有流程约束",
        ).stdout.strip().split()[-1]
        second = run_cli(
            self.tmp,
            "rule",
            "add",
            "--title",
            "阶段记录默认不提交也不推送",
            "--claim",
            "checkpoint 与 session end 共享保存范围，但中途记录默认不提交也不推送。",
            "--source-kind",
            "implemented",
            "--rule-kind",
            "recording",
            "--scope-kind",
            "global",
            "--status",
            "active",
            "--supersedes-rule-id",
            first,
            "--note",
            "实现后确认的新口径",
        ).stdout.strip().split()[-1]

        index = run_cli(self.tmp, "context", "index")
        snapshot_text = (self.tmp / ".auto_iter" / "rules" / "current_effective.md").read_text(encoding="utf-8")

        self.assertTrue((self.tmp / ".auto_iter" / "rules" / "superseded" / f"{first}.md").exists())
        self.assertTrue((self.tmp / ".auto_iter" / "rules" / "active" / f"{second}.md").exists())
        self.assertIn("- path: .auto_iter/rules/current_effective.md", index.stdout)
        self.assertIn(f"- path: .auto_iter/rules/active/{second}.md", index.stdout)
        self.assertIn(f"- path: .auto_iter/rules/superseded/{first}.md", index.stdout)
        self.assertIn(second, snapshot_text)
        self.assertIn("阶段记录默认不提交也不推送", snapshot_text)
        self.assertNotIn("## 阶段记录默认不提交\n", snapshot_text)

    def test_search_query_finds_rule_projection(self):
        run_cli(self.tmp, "init")
        rule_id = run_cli(
            self.tmp,
            "rule",
            "add",
            "--title",
            "结束 session 前必须生成 handoff",
            "--claim",
            "用户要求结束当前 session 或做 handoff 时，先生成并校验 handoff。",
            "--source-kind",
            "user_stated",
            "--rule-kind",
            "exit",
            "--scope-kind",
            "global",
            "--status",
            "active",
            "--note",
            "session end workflow",
        ).stdout.strip().split()[-1]

        queried = run_cli(
            self.tmp,
            "search",
            "query",
            "--text",
            "session end handoff rule",
            "--limit",
            "5",
            "--explain",
        )

        self.assertIn("source=rule", queried.stdout)
        self.assertIn(f"id={rule_id}", queried.stdout)
        self.assertIn(f"path: .auto_iter/rules/active/{rule_id}.md", queried.stdout)
        self.assertIn("next: auto-iter context show", queried.stdout)
        self.assertIn("结束 session 前必须生成 handoff", queried.stdout)


if __name__ == "__main__":
    unittest.main()
