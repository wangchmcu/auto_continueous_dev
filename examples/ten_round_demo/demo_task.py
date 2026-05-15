from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DATASET = [(float(x), 2.0 * float(x) + 1.5) for x in range(10)]


def evaluate_config(config: dict[str, Any]) -> dict[str, dict[str, float | str]]:
    weight = float(config["weight"])
    offset = float(config["offset"])
    objective = str(config.get("objective", "minimize_error"))
    absolute_errors = [abs((weight * x + offset) - target) for x, target in DATASET]
    mean_absolute_error = sum(absolute_errors) / len(absolute_errors)
    max_absolute_error = max(absolute_errors)

    if objective == "max_value_reward":
        objective_score = -(weight * DATASET[-1][0] + offset)
        objective_direction = "lower_is_better"
    else:
        objective_score = mean_absolute_error
        objective_direction = "lower_is_better"

    return {
        "mean_absolute_error": {
            "value": round(mean_absolute_error, 6),
            "unit": "target_units",
            "direction": "lower_is_better",
        },
        "max_absolute_error": {
            "value": round(max_absolute_error, 6),
            "unit": "target_units",
            "direction": "lower_is_better",
        },
        "objective_score": {
            "value": round(objective_score, 6),
            "unit": "score",
            "direction": objective_direction,
        },
    }


def write_report(config: dict[str, Any], metrics: dict[str, dict[str, float | str]], path: Path) -> None:
    lines = [
        "# Ten Round Demo Report",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Metrics",
    ]
    for name, metric in metrics.items():
        lines.append(f"- {name}: {metric['value']} {metric['unit']} ({metric['direction']})")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    metrics_path = Path(args.metrics).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    metrics = evaluate_config(config)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(config, metrics, report_path)
    print(f"mean_absolute_error={metrics['mean_absolute_error']['value']}")
    print(f"objective_score={metrics['objective_score']['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
