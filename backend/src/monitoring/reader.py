"""
OpsPulse Pipeline Observability - Airflow Metadata Reader.

Performs read-only extraction of Airflow DAG runs, task instance telemetry,
and XCom batch associations directly from the Airflow metadata database.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .models import PipelineRunMetric, PipelineTaskMetric

DEFAULT_AIRFLOW_LOGS_DIR = Path("/home/mg_magic/airflow/logs")


def get_airflow_metadata_engine(database_url: Optional[str] = None) -> Engine:
    """
    Creates a read-only SQLAlchemy engine for the Airflow metadata database.
    Does not hardcode credentials.
    """
    url = database_url or os.getenv("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN") or os.getenv("AIRFLOW_DATABASE_URL")
    
    if not url:
        # Check if OPSPULSE_DATABASE_URL exists and derive airflow_metadata DB on same host
        warehouse_url = os.getenv("OPSPULSE_DATABASE_URL")
        if warehouse_url and "opspulse_dw" in warehouse_url:
            url = warehouse_url.replace("opspulse_dw", "airflow_metadata")

    if not url:
        raise ValueError(
            "Airflow metadata connection string not found. "
            "Set AIRFLOW__DATABASE__SQL_ALCHEMY_CONN or AIRFLOW_DATABASE_URL."
        )

    return create_engine(url, pool_pre_ping=True, future=True)


class AirflowMetadataReader:
    """
    Reader for querying Airflow execution metrics without mutating metadata.
    """

    def __init__(self, engine: Engine, logs_dir: Optional[Path] = None):
        self.engine = engine
        self.logs_dir = logs_dir or DEFAULT_AIRFLOW_LOGS_DIR

    def get_dag_runs(self, dag_id: str, limit: int = 50) -> List[Dict]:
        """Queries historical DAG runs for the given dag_id."""
        query = text("""
            SELECT dag_id, run_id, state, logical_date, start_date, end_date, run_type
            FROM dag_run
            WHERE dag_id = :dag_id
            ORDER BY start_date DESC NULLS LAST
            LIMIT :limit
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"dag_id": dag_id, "limit": limit}).mappings().fetchall()
            return [dict(r) for r in rows]

    def get_latest_dag_run(self, dag_id: str) -> Optional[Dict]:
        """Retrieves the most recent DAG run for the specified dag_id."""
        runs = self.get_dag_runs(dag_id=dag_id, limit=1)
        return runs[0] if runs else None

    def get_run_batch_id(self, dag_id: str, run_id: str) -> Optional[str]:
        """
        Extracts the batch_id associated with this run from XComs.
        Checks xcom_v2 (Airflow 3) or xcom (Airflow 2).
        """
        queries = [
            # Airflow 3 (xcom_v2)
            """
            SELECT x.value
            FROM xcom_v2 x
            JOIN task_instance ti ON x.task_instance_id = ti.id
            WHERE ti.dag_id = :dag_id AND ti.run_id = :run_id AND ti.task_id = 'run_ingestion' AND x.key = 'return_value'
            LIMIT 1
            """,
            # Airflow 2 (xcom)
            """
            SELECT value
            FROM xcom
            WHERE dag_id = :dag_id AND run_id = :run_id AND task_id = 'run_ingestion' AND key = 'return_value'
            LIMIT 1
            """,
            # Check any transform task return_value
            """
            SELECT x.value
            FROM xcom_v2 x
            JOIN task_instance ti ON x.task_instance_id = ti.id
            WHERE ti.dag_id = :dag_id AND ti.run_id = :run_id AND ti.task_id LIKE 'transform_%' AND x.key = 'return_value'
            LIMIT 1
            """
        ]

        with self.engine.connect() as conn:
            for q in queries:
                try:
                    val = conn.execute(text(q), {"dag_id": dag_id, "run_id": run_id}).scalar()
                    if val:
                        if isinstance(val, str) and val.startswith("batch_"):
                            return val
                        elif isinstance(val, dict) and "batch_id" in val:
                            return str(val["batch_id"])
                        elif isinstance(val, str):
                            # Try parsing json if serialized
                            try:
                                d = json.loads(val)
                                if isinstance(d, dict) and "batch_id" in d:
                                    return str(d["batch_id"])
                                if isinstance(d, str) and d.startswith("batch_"):
                                    return d
                            except Exception:
                                pass
                except Exception:
                    continue

        return None

    def get_task_instances(self, dag_id: str, run_id: str) -> List[Dict]:
        """Queries task instances for the specified DAG run."""
        query = text("""
            SELECT task_id, state, start_date, end_date, duration, try_number, max_tries
            FROM task_instance
            WHERE dag_id = :dag_id AND run_id = :run_id
            ORDER BY start_date ASC NULLS LAST
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"dag_id": dag_id, "run_id": run_id}).mappings().fetchall()
            return [dict(r) for r in rows]

    def get_historical_task_averages(self, dag_id: str) -> Dict[str, float]:
        """
        Computes historical average duration per task across prior successful runs.
        """
        query = text("""
            SELECT task_id, AVG(duration) as avg_duration
            FROM task_instance
            WHERE dag_id = :dag_id AND state = 'success' AND duration IS NOT NULL
            GROUP BY task_id
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"dag_id": dag_id}).fetchall()
            return {r[0]: round(float(r[1]), 3) for r in rows if r[1] is not None}

    def extract_task_error(self, dag_id: str, run_id: str, task_id: str, try_number: int = 1) -> Optional[str]:
        """
        Extracts error summary for a failed task instance from log file if present.
        """
        log_file = (
            self.logs_dir
            / f"dag_id={dag_id}"
            / f"run_id={run_id}"
            / f"task_id={task_id}"
            / f"attempt={try_number}.log"
        )
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                # Find lines containing ERROR, Exception, Traceback
                err_lines = [l for l in lines if any(k in l for k in ["ERROR", "Exception", "RuntimeError", "ValueError"])]
                if err_lines:
                    return err_lines[-1][:400]
            except Exception:
                pass
        return None

    def build_run_metric(self, dag_id: str, run_id: str, batch_id: Optional[str] = None) -> Tuple[PipelineRunMetric, List[PipelineTaskMetric]]:
        """
        Constructs PipelineRunMetric and list of PipelineTaskMetric objects for the run.
        """
        # Fetch run row
        runs = self.get_dag_runs(dag_id=dag_id, limit=200)
        target_run = next((r for r in runs if r["run_id"] == run_id), None)
        if not target_run:
            raise ValueError(f"DAG run '{run_id}' not found for dag '{dag_id}'.")

        # Discover batch_id if not supplied
        resolved_batch_id = batch_id or self.get_run_batch_id(dag_id=dag_id, run_id=run_id)

        # Task instances
        tis = self.get_task_instances(dag_id=dag_id, run_id=run_id)
        historical_avgs = self.get_historical_task_averages(dag_id=dag_id)

        successful_count = 0
        failed_count = 0
        skipped_count = 0
        retried_count = 0

        task_metrics: List[PipelineTaskMetric] = []

        for ti in tis:
            state = ti.get("state") or "unknown"
            duration = float(ti["duration"]) if ti.get("duration") is not None else None
            try_num = int(ti.get("try_number") or 1)
            max_retries = int(ti.get("max_tries") or 0)

            if state == "success":
                successful_count += 1
            elif state in ("failed", "upstream_failed"):
                failed_count += 1
            elif state == "skipped":
                skipped_count += 1

            if try_num > 1:
                retried_count += 1

            error_msg = None
            if state in ("failed", "upstream_failed"):
                error_msg = self.extract_task_error(
                    dag_id=dag_id, run_id=run_id, task_id=ti["task_id"], try_number=try_num
                ) or f"Task execution ended with state '{state}'."

            # Calculate historical comparison metrics
            t_id = ti["task_id"]
            hist_avg = historical_avgs.get(t_id)
            variance_pct = None
            if hist_avg is not None and hist_avg > 0 and duration is not None:
                variance_pct = round(((duration - hist_avg) / hist_avg) * 100.0, 2)

            task_metrics.append(
                PipelineTaskMetric(
                    dag_id=dag_id,
                    dag_run_id=run_id,
                    task_id=t_id,
                    task_state=state,
                    start_time=ti["start_date"].isoformat() if ti.get("start_date") else None,
                    end_time=ti["end_date"].isoformat() if ti.get("end_date") else None,
                    duration_seconds=duration,
                    try_number=try_num,
                    max_retries=max_retries,
                    error_message=error_msg,
                    historical_avg_duration_seconds=hist_avg,
                    duration_variance_pct=variance_pct,
                )
            )

        # Calculate run duration
        run_duration = None
        if target_run.get("start_date") and target_run.get("end_date"):
            delta = (target_run["end_date"] - target_run["start_date"]).total_seconds()
            run_duration = round(delta, 2)

        run_metric = PipelineRunMetric(
            dag_id=dag_id,
            dag_run_id=run_id,
            batch_id=resolved_batch_id,
            run_status=target_run.get("state") or "unknown",
            logical_date=target_run["logical_date"].isoformat() if target_run.get("logical_date") else None,
            start_time=target_run["start_date"].isoformat() if target_run.get("start_date") else None,
            end_time=target_run["end_date"].isoformat() if target_run.get("end_date") else None,
            total_duration_seconds=run_duration,
            successful_tasks=successful_count,
            failed_tasks=failed_count,
            skipped_tasks=skipped_count,
            retried_tasks=retried_count,
            total_tasks=len(tis),
        )

        return run_metric, task_metrics
