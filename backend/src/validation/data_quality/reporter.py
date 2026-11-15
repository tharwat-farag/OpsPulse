"""
OpsPulse Data Quality Framework - Reporting Engine.

Generates machine-readable JSON reports and human-readable CSV reports
under `data/quality_reports/`. Ensures traceability, summary analytics,
and strict non-exposure of sensitive PII data.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .models import BatchQualityReport, CheckResult, DatasetQualitySummary


def get_default_reports_dir() -> Path:
    """Returns the default project directory for data quality reports."""
    # backend/src/validation/data_quality -> parents[4] is project root
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "data" / "quality_reports"


def format_json_report(report: BatchQualityReport) -> Dict:
    """Produces the structured dictionary for JSON export."""
    return report.to_dict()


def generate_csv_rows(report: BatchQualityReport) -> List[Dict]:
    """Flattens check results into tabular rows for CSV export."""
    rows = []
    for r in report.check_results:
        samples_str = ";".join(str(s) for s in r.sample_failed_records) if r.sample_failed_records else ""
        rows.append({
            "dataset": r.dataset,
            "check_name": r.check_name,
            "check_category": r.check_category,
            "total_records": r.total_records,
            "passed_records": r.passed_records,
            "failed_records": r.failed_records,
            "quality_score": r.quality_score,
            "status": r.status,
            "severity": r.severity,
            "execution_timestamp": r.execution_timestamp,
            "batch_id": r.batch_id,
            "details": r.details,
            "sample_failed_records": samples_str,
        })
    return rows


def save_quality_reports(
    report: BatchQualityReport,
    output_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    """
    Saves JSON and CSV reports to the target directory.
    Creates directory if it does not exist.
    Also creates or overwrites latest_quality_report copies.

    Returns:
        Tuple of (json_path, csv_path)
    """
    reports_dir = output_dir or get_default_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)

    batch_clean = report.batch_id.replace("/", "_").replace("\\", "_")
    json_path = reports_dir / f"quality_report_{batch_clean}.json"
    csv_path = reports_dir / f"quality_report_{batch_clean}.csv"

    latest_json_path = reports_dir / "latest_quality_report.json"
    latest_csv_path = reports_dir / "latest_quality_report.csv"

    # 1. Write JSON Report
    report_dict = format_json_report(report)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    # 2. Write CSV Report
    csv_rows = generate_csv_rows(report)
    csv_fieldnames = [
        "dataset",
        "check_name",
        "check_category",
        "total_records",
        "passed_records",
        "failed_records",
        "quality_score",
        "status",
        "severity",
        "execution_timestamp",
        "batch_id",
        "details",
        "sample_failed_records",
    ]

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    with open(latest_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    return json_path, csv_path
