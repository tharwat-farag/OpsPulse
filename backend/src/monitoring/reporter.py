"""
OpsPulse Pipeline Observability - Report Generation Engine.

Generates machine-readable JSON and human-readable CSV monitoring reports
under `data/monitoring_reports/`. Distinguishes unavailable metrics from zero values
and includes historical comparisons.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import PipelineObservabilityReport

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MONITORING_REPORTS_DIR = PROJECT_ROOT / "data" / "monitoring_reports"


def save_monitoring_reports(
    report: PipelineObservabilityReport,
    output_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    """
    Saves JSON and CSV monitoring reports for the given pipeline execution.
    Creates target directory if necessary.
    """
    reports_dir = output_dir or DEFAULT_MONITORING_REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    clean_run_id = (
        report.dag_run_id.replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("+", "_")
    )
    json_path = reports_dir / f"monitoring_report_{clean_run_id}.json"
    csv_path = reports_dir / f"monitoring_report_{clean_run_id}.csv"

    latest_json_path = reports_dir / "latest_monitoring_report.json"
    latest_csv_path = reports_dir / "latest_monitoring_report.csv"

    # 1. JSON Report
    report_dict = report.to_dict()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    # 2. CSV Report (Flattened Task Performance & Status)
    csv_fieldnames = [
        "dag_id",
        "dag_run_id",
        "batch_id",
        "task_id",
        "task_state",
        "start_time",
        "end_time",
        "duration_seconds",
        "historical_avg_seconds",
        "duration_variance_pct",
        "try_number",
        "max_retries",
        "error_message",
    ]

    csv_rows = []
    for t in report.task_metrics:
        csv_rows.append({
            "dag_id": t.dag_id,
            "dag_run_id": t.dag_run_id,
            "batch_id": report.batch_id or "N/A",
            "task_id": t.task_id,
            "task_state": t.task_state,
            "start_time": t.start_time or "N/A",
            "end_time": t.end_time or "N/A",
            "duration_seconds": t.duration_seconds if t.duration_seconds is not None else "N/A",
            "historical_avg_seconds": t.historical_avg_duration_seconds if t.historical_avg_duration_seconds is not None else "N/A",
            "duration_variance_pct": t.duration_variance_pct if t.duration_variance_pct is not None else "N/A",
            "try_number": t.try_number,
            "max_retries": t.max_retries,
            "error_message": t.error_message or "N/A",
        })

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    with open(latest_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    return json_path, csv_path
