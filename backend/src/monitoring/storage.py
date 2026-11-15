"""
OpsPulse Pipeline Observability - PostgreSQL Monitoring Storage.

Provides idempotent persistence for run metrics, task metrics,
data volume measurements, and failure events in the `monitoring` schema.
"""

from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import (
    PipelineDataVolumeMetric,
    PipelineFailureEvent,
    PipelineRunMetric,
    PipelineTaskMetric,
)


def persist_observability_metrics(
    engine: Engine,
    run_metric: PipelineRunMetric,
    task_metrics: List[PipelineTaskMetric],
    volume_metrics: List[PipelineDataVolumeMetric],
    failure_events: List[PipelineFailureEvent],
) -> None:
    """
    Persists all derived observability metrics into the PostgreSQL `monitoring` schema
    within an idempotent transaction.
    """
    with engine.begin() as conn:
        # 1. Upsert Pipeline Run Metric
        run_upsert_sql = text("""
            INSERT INTO monitoring.pipeline_run_metrics (
                dag_id, dag_run_id, batch_id, run_status, logical_date,
                start_time, end_time, total_duration_seconds,
                successful_tasks, failed_tasks, skipped_tasks, retried_tasks, total_tasks,
                collected_at
            ) VALUES (
                :dag_id, :dag_run_id, :batch_id, :run_status, :logical_date,
                :start_time, :end_time, :total_duration_seconds,
                :successful_tasks, :failed_tasks, :skipped_tasks, :retried_tasks, :total_tasks,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (dag_id, dag_run_id) DO UPDATE SET
                batch_id = EXCLUDED.batch_id,
                run_status = EXCLUDED.run_status,
                logical_date = EXCLUDED.logical_date,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                total_duration_seconds = EXCLUDED.total_duration_seconds,
                successful_tasks = EXCLUDED.successful_tasks,
                failed_tasks = EXCLUDED.failed_tasks,
                skipped_tasks = EXCLUDED.skipped_tasks,
                retried_tasks = EXCLUDED.retried_tasks,
                total_tasks = EXCLUDED.total_tasks,
                collected_at = CURRENT_TIMESTAMP;
        """)

        conn.execute(run_upsert_sql, {
            "dag_id": run_metric.dag_id,
            "dag_run_id": run_metric.dag_run_id,
            "batch_id": run_metric.batch_id,
            "run_status": run_metric.run_status,
            "logical_date": run_metric.logical_date,
            "start_time": run_metric.start_time,
            "end_time": run_metric.end_time,
            "total_duration_seconds": run_metric.total_duration_seconds,
            "successful_tasks": run_metric.successful_tasks,
            "failed_tasks": run_metric.failed_tasks,
            "skipped_tasks": run_metric.skipped_tasks,
            "retried_tasks": run_metric.retried_tasks,
            "total_tasks": run_metric.total_tasks,
        })

        # 2. Idempotent Upsert for Task Metrics
        task_upsert_sql = text("""
            INSERT INTO monitoring.pipeline_task_metrics (
                dag_id, dag_run_id, task_id, task_state, start_time,
                end_time, duration_seconds, try_number, max_retries,
                error_message, collected_at
            ) VALUES (
                :dag_id, :dag_run_id, :task_id, :task_state, :start_time,
                :end_time, :duration_seconds, :try_number, :max_retries,
                :error_message, CURRENT_TIMESTAMP
            )
            ON CONFLICT (dag_run_id, task_id) DO UPDATE SET
                task_state = EXCLUDED.task_state,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                duration_seconds = EXCLUDED.duration_seconds,
                try_number = EXCLUDED.try_number,
                max_retries = EXCLUDED.max_retries,
                error_message = EXCLUDED.error_message,
                collected_at = CURRENT_TIMESTAMP;
        """)

        for tm in task_metrics:
            conn.execute(task_upsert_sql, {
                "dag_id": tm.dag_id,
                "dag_run_id": tm.dag_run_id,
                "task_id": tm.task_id,
                "task_state": tm.task_state,
                "start_time": tm.start_time,
                "end_time": tm.end_time,
                "duration_seconds": tm.duration_seconds,
                "try_number": tm.try_number,
                "max_retries": tm.max_retries,
                "error_message": tm.error_message,
            })

        # 3. Idempotent Upsert for Data Volume Metrics
        vol_upsert_sql = text("""
            INSERT INTO monitoring.pipeline_data_volume_metrics (
                dag_run_id, batch_id, layer, metric_name, record_count,
                metric_source, collected_at
            ) VALUES (
                :dag_run_id, :batch_id, :layer, :metric_name, :record_count,
                :metric_source, CURRENT_TIMESTAMP
            )
            ON CONFLICT (dag_run_id, batch_id, layer, metric_name) DO UPDATE SET
                record_count = EXCLUDED.record_count,
                metric_source = EXCLUDED.metric_source,
                collected_at = CURRENT_TIMESTAMP;
        """)

        for vm in volume_metrics:
            conn.execute(vol_upsert_sql, {
                "dag_run_id": vm.dag_run_id,
                "batch_id": vm.batch_id,
                "layer": vm.layer,
                "metric_name": vm.metric_name,
                "record_count": vm.record_count,
                "metric_source": vm.metric_source,
            })

        # 4. Idempotent Refresh for Failure Events
        conn.execute(
            text("DELETE FROM monitoring.pipeline_failure_events WHERE dag_run_id = :dag_run_id"),
            {"dag_run_id": run_metric.dag_run_id},
        )

        fail_insert_sql = text("""
            INSERT INTO monitoring.pipeline_failure_events (
                dag_run_id, batch_id, task_id, failure_category,
                error_type, error_message, failed_at, collected_at
            ) VALUES (
                :dag_run_id, :batch_id, :task_id, :failure_category,
                :error_type, :error_message, :failed_at, CURRENT_TIMESTAMP
            );
        """)

        for fe in failure_events:
            conn.execute(fail_insert_sql, {
                "dag_run_id": fe.dag_run_id,
                "batch_id": fe.batch_id,
                "task_id": fe.task_id,
                "failure_category": fe.failure_category,
                "error_type": fe.error_type,
                "error_message": fe.error_message,
                "failed_at": fe.failed_at,
            })

    print(f"Persisted monitoring telemetry for run '{run_metric.dag_run_id}' (Tasks: {len(task_metrics)}, Volumes: {len(volume_metrics)}, Failures: {len(failure_events)}).")
