"""
OpsPulse Data Quality Framework - Execution Runner.

Main execution entry point for CLI and Airflow pipeline integration.
Executes the QualitySuite against the target Silver batch, generates
reports in data/quality_reports/, and enforces quality gates.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

if __package__ in (None, ""):
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from validation.data_quality.models import BatchQualityReport, CheckStatus
    from validation.data_quality.reporter import get_default_reports_dir, save_quality_reports
    from validation.data_quality.suite import DATASETS, QualitySuite
else:
    from .models import BatchQualityReport, CheckStatus
    from .reporter import get_default_reports_dir, save_quality_reports
    from .suite import DATASETS, QualitySuite

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


def run_data_quality_checks(
    batch_id: str,
    silver_dir: Optional[Path] = None,
    output_reports_dir: Optional[Path] = None,
    halt_on_critical_failure: bool = True,
) -> BatchQualityReport:
    """
    Executes all Data Quality validations for a specific Silver batch.
    
    Args:
        batch_id: The batch identifier (e.g., 'batch_20261115_051056_1d64c5da')
        silver_dir: Path to Silver layer directory
        output_reports_dir: Path to directory for saving reports
        halt_on_critical_failure: Whether to raise RuntimeError if critical checks fail

    Returns:
        The generated BatchQualityReport
    """
    if not batch_id or not batch_id.strip():
        raise ValueError("A valid batch_id is required.")

    batch_id = batch_id.strip()
    target_silver = silver_dir or SILVER_DIR

    print("=" * 80)
    print("OPSPULSE - AUTOMATED DATA QUALITY GATE")
    print(f"Batch ID: {batch_id}")
    print("=" * 80)

    # Initialize and execute quality suite
    suite = QualitySuite.from_batch_directory(batch_id, target_silver)
    report = suite.run()

    # Save machine-readable JSON and human-readable CSV reports
    json_path, csv_path = save_quality_reports(report, output_reports_dir)

    # Print summary table
    summary_data = []
    for s in report.dataset_summaries:
        summary_data.append({
            "Dataset": s.dataset,
            "Records": f"{s.total_records:,}",
            "Checks": s.total_checks,
            "Passed": s.passed_checks,
            "Failed": s.failed_checks,
            "Score": f"{s.quality_score:.1f}%",
            "Status": s.status,
        })

    summary_df = pd.DataFrame(summary_data)
    print("\nDataset Quality Summary:")
    print(summary_df.to_string(index=False))

    print("\n" + "-" * 80)
    print(f"Overall Quality Score: {report.overall_quality_score:.2f}%")
    print(f"Total Checks Executed: {report.total_checks_executed}")
    print(f"Passed Checks:         {report.passed_checks}")
    print(f"Failed Checks:         {report.failed_checks}")
    print(f"Warning Checks:        {report.warning_checks}")
    print(f"Batch Status:          {report.status}")
    print(f"Reports Generated:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print("-" * 80)

    # Print failure details if any
    if report.failed_checks > 0:
        print("\nDATA QUALITY FAILURES DETECTED:")
        for dataset, failures in report.dataset_failures.items():
            print(f"\n  [{dataset.upper()}] ({len(failures)} failures):")
            for f in failures:
                print(f"    - {f['check_name']} ({f['check_category']}): {f['details']}")
                if f.get("sample_failed_records"):
                    print(f"      Samples: {f['sample_failed_records'][:5]}")

    # Enforce quality gate
    if report.status == CheckStatus.FAILED.value and halt_on_critical_failure:
        raise RuntimeError(
            f"Data Quality Gate FAILED for batch '{batch_id}'. "
            f"{report.failed_checks} critical checks failed. Halting downstream loading."
        )

    print("\nDATA QUALITY GATE PASSED.")
    return report


def main(batch_id: str, halt_on_failure: bool = True) -> Dict:
    """
    Airflow task / callable entry point matching project conventions.
    Returns summary dictionary.
    """
    report = run_data_quality_checks(
        batch_id=batch_id,
        halt_on_critical_failure=halt_on_failure,
    )
    return {
        "batch_id": report.batch_id,
        "overall_quality_score": report.overall_quality_score,
        "total_checks": report.total_checks_executed,
        "passed_checks": report.passed_checks,
        "failed_checks": report.failed_checks,
        "warning_checks": report.warning_checks,
        "status": report.status,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run OpsPulse Data Quality Framework."
    )
    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to validate.",
    )
    parser.add_argument(
        "--no-halt",
        action="store_true",
        help="Do not raise exception on quality failures.",
    )

    args = parser.parse_args()
    try:
        main(args.batch_id, halt_on_failure=not args.no_halt)
    except Exception as exc:
        print(f"\nExecution failed: {exc}", file=sys.stderr)
        sys.exit(1)
