"""
OpsPulse Pipeline Observability - Main Collection Orchestrator.

Coordinates metadata reading, volume extraction, failure classification,
persistence, and report generation for a single DAG run.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .classifier import classify_task_failure
from .models import PipelineFailureEvent, PipelineObservabilityReport
from .reader import AirflowMetadataReader, get_airflow_metadata_engine
from .reporter import save_monitoring_reports
from .schema import init_monitoring_schema
from .storage import persist_observability_metrics
from .volume_extractor import extract_data_volume_metrics

# Import warehouse DB engine at module level for testability (patchable).
# Lazy import fallback prevents ImportError in environments without warehouse deps.
try:
    from warehouse.db_connection import get_database_engine  # type: ignore
except ImportError:  # pragma: no cover
    def get_database_engine():  # type: ignore  # noqa: E301
        """Fallback when warehouse package is unavailable."""
        raise ImportError("warehouse.db_connection not available in this environment.")


# ---------------------------------------------------------------------------
# Project-root helper (3 levels up: monitoring → src → backend → project root)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def collect_observability(
    dag_id: str = "opspulse_pipeline",
    dag_run_id: Optional[str] = None,
    *,
    persist: bool = True,
    report: bool = True,
    project_root: Optional[Path] = None,
) -> PipelineObservabilityReport:
    """
    Collects full observability telemetry for a DAG run.

    Steps:
      1. Connect to the Airflow metadata database (read-only).
      2. Resolve the target run_id (latest if not supplied).
      3. Build PipelineRunMetric + PipelineTaskMetric list.
      4. Extract PipelineDataVolumeMetric list from files and Gold DB.
      5. Classify failed tasks into PipelineFailureEvent objects.
      6. Persist all metrics into monitoring.* tables (idempotent upsert).
      7. Generate JSON + CSV reports under data/monitoring_reports/.
      8. Return PipelineObservabilityReport.

    Args:
        dag_id:        Airflow DAG identifier.
        dag_run_id:    Specific DAG run ID; uses latest run when None.
        persist:       Write metrics to PostgreSQL monitoring schema.
        report:        Write JSON/CSV files to data/monitoring_reports/.
        project_root:  Override for the project root path (useful in tests).

    Returns:
        PipelineObservabilityReport with all collected telemetry.
    """
    root = project_root or _PROJECT_ROOT
    collection_ts = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1. Connect to Airflow metadata database (READ-ONLY)
    # ------------------------------------------------------------------
    airflow_engine = get_airflow_metadata_engine()
    reader = AirflowMetadataReader(engine=airflow_engine)

    # ------------------------------------------------------------------
    # 2. Resolve target run_id
    # ------------------------------------------------------------------
    if dag_run_id:
        resolved_run_id = dag_run_id
    else:
        latest = reader.get_latest_dag_run(dag_id=dag_id)
        if not latest:
            raise RuntimeError(
                f"No DAG runs found for dag_id='{dag_id}'. "
                "Ensure the pipeline has executed at least once."
            )
        resolved_run_id = latest["run_id"]

    print(f"[Observability] Collecting metrics for run: {resolved_run_id}")

    # ------------------------------------------------------------------
    # 3. Build run metric + task metrics
    # ------------------------------------------------------------------
    run_metric, task_metrics = reader.build_run_metric(
        dag_id=dag_id,
        run_id=resolved_run_id,
    )
    batch_id = run_metric.batch_id

    print(
        f"[Observability] Run status: {run_metric.run_status} | "
        f"Tasks: {run_metric.total_tasks} | "
        f"Batch: {batch_id or 'N/A'}"
    )

    # ------------------------------------------------------------------
    # 4. Extract data volume metrics
    # ------------------------------------------------------------------
    volume_metrics = []
    if batch_id:
        try:
            warehouse_engine = get_database_engine() if get_database_engine else None
        except Exception as exc:
            print(f"[Observability] Warning: Could not connect to warehouse DB: {exc}")
            warehouse_engine = None

        volume_metrics = extract_data_volume_metrics(
            batch_id=batch_id,
            dag_run_id=resolved_run_id,
            warehouse_engine=warehouse_engine,
            project_root=root,
        )
        print(f"[Observability] Volume metrics collected: {len(volume_metrics)}")
    else:
        print("[Observability] No batch_id resolved; skipping volume metrics.")

    # ------------------------------------------------------------------
    # 5. Classify failures
    # ------------------------------------------------------------------
    failure_events = []
    for tm in task_metrics:
        if tm.task_state in ("failed", "upstream_failed"):
            category, error_type = classify_task_failure(
                task_id=tm.task_id,
                error_message=tm.error_message,
                exception_type=None,
            )
            failure_events.append(
                PipelineFailureEvent(
                    dag_run_id=resolved_run_id,
                    batch_id=batch_id,
                    task_id=tm.task_id,
                    failure_category=category,
                    error_type=error_type,
                    error_message=tm.error_message,
                    failed_at=tm.end_time,
                )
            )

    if failure_events:
        print(f"[Observability] Failure events classified: {len(failure_events)}")

    # ------------------------------------------------------------------
    # 6. Build consolidated report object
    # ------------------------------------------------------------------
    obs_report = PipelineObservabilityReport(
        dag_id=dag_id,
        dag_run_id=resolved_run_id,
        batch_id=batch_id,
        collection_timestamp=collection_ts,
        run_metric=run_metric,
        task_metrics=task_metrics,
        volume_metrics=volume_metrics,
        failure_events=failure_events,
    )

    # ------------------------------------------------------------------
    # 7. Persist to PostgreSQL monitoring schema
    # ------------------------------------------------------------------
    if persist:
        try:
            warehouse_engine = get_database_engine() if get_database_engine else None
            if warehouse_engine:
                # Ensure schema exists (idempotent)
                init_monitoring_schema(engine=warehouse_engine)
                persist_observability_metrics(
                    engine=warehouse_engine,
                    run_metric=run_metric,
                    task_metrics=task_metrics,
                    volume_metrics=volume_metrics,
                    failure_events=failure_events,
                )
        except Exception as exc:
            print(f"[Observability] Warning: Could not persist to monitoring schema: {exc}")

    # ------------------------------------------------------------------
    # 8. Generate file reports
    # ------------------------------------------------------------------
    if report:
        try:
            json_path, csv_path = save_monitoring_reports(
                report=obs_report,
                output_dir=root / "data" / "monitoring_reports",
            )
            print(f"[Observability] JSON report: {json_path}")
            print(f"[Observability] CSV  report: {csv_path}")
        except Exception as exc:
            print(f"[Observability] Warning: Could not write reports: {exc}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(
        f"\n[Observability] Collection complete — "
        f"Run: {resolved_run_id[:40]}... | "
        f"Tasks: {len(task_metrics)} | "
        f"Volumes: {len(volume_metrics)} | "
        f"Failures: {len(failure_events)}"
    )

    return obs_report
