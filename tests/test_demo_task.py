import json
import tempfile
import unittest
from pathlib import Path

from examples.ten_round_demo.demo_task import evaluate_config, main


class DemoTaskTests(unittest.TestCase):
    def test_perfect_linear_config_has_zero_mean_absolute_error(self):
        metrics = evaluate_config({"weight": 2.0, "offset": 1.5, "objective": "minimize_error"})

        self.assertEqual(metrics["mean_absolute_error"]["value"], 0.0)
        self.assertEqual(metrics["mean_absolute_error"]["direction"], "lower_is_better")

    def test_main_writes_metrics_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            metrics = root / "metrics.json"
            report = root / "report.md"
            config.write_text(
                json.dumps({"weight": 2.0, "offset": 1.5, "objective": "minimize_error"}),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--config",
                    str(config),
                    "--metrics",
                    str(metrics),
                    "--report",
                    str(report),
                ]
            )

            self.assertEqual(exit_code, 0)
            saved = json.loads(metrics.read_text(encoding="utf-8"))
            self.assertEqual(saved["mean_absolute_error"]["value"], 0.0)
            self.assertIn("mean_absolute_error", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
