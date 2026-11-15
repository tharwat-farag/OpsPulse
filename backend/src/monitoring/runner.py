"""
OpsPulse Pipeline Observability - CLI & Airflow Task Entry Point.

Usage:
    python backend/src/monitoring/runner.py
    python backend/src/monitoring/runner.py --dag-id opspulse_pipeline
    python backend/src/monitoring/runner.py --dag-run-id manual__2026-11-15T05:05:32.814530+00:00
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from monitoring.collector import collect_observability
else:
    from .collector import collect_observability


def main(
    dag_id: str = "opspulse_pipeline",
    dag_run_id: Optional[str] = None,
    *,
    persist: bool = True,
    report: bool = True,
) -> dict:
    """
    Airflow-compatible callable entry point.

    Can be called directly by Airflow's PythonOperator/task decorator, or run
    from the command line. Returns a dict summary of collected telemetry.

    Args:
        dag_id:     Target Airflow DAG identifier.
        dag_run_id: Specific run_id to collect; uses latest when None.
        persist:    Write to PostgreSQL monitoring schema.
        report:     Write JSON/CSV reports to data/monitoring_reports/.

    Returns:
        Dict with collection summary suitable for XCom serialization.
    """
    obs_report = collect_observability(
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        persist=persist,
        report=report,
    )

    return {
        "dag_id": obs_report.dag_id,
        "dag_run_id": obs_report.dag_run_id,
        "batch_id": obs_report.batch_id,
        "run_status": obs_report.run_metric.run_status,
        "tasks_collected": len(obs_report.task_metrics),
        "volume_metrics_collected": len(obs_report.volume_metrics),
        "failure_events": len(obs_report.failure_events),
        "collection_timestamp": obs_report.collection_timestamp,
    }


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpsPulse Pipeline Observability Collector",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dag-id",
        default="opspulse_pipeline",
        help="Airflow DAG identifier to collect metrics for.",
    )
    parser.add_argument(
        "--dag-run-id",
        default=None,
        help="Specific DAG run ID. If omitted, the latest run is collected.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        default=False,
        help="Skip persisting to PostgreSQL (dry-run / report-only mode).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Skip writing JSON/CSV report files.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()

    result = main(
        dag_id=args.dag_id,
        dag_run_id=args.dag_run_id,
        persist=not args.no_persist,
        report=not args.no_report,
    )

    print("\n--- Observability Collection Summary ---")
    for key, value in result.items():
        print(f"  {key}: {value}")

    sys.exit(0)
