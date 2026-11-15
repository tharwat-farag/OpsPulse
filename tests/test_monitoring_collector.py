"""
Unit tests for monitoring.collector — full observability orchestration.

All external dependencies (Airflow DB, warehouse DB, file I/O) are mocked
so tests run without any infrastructure.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from monitoring.models import (
    FailureCategory,
    PipelineDataVolumeMetric,
    PipelineFailureEvent,
    PipelineObservabilityReport,
    PipelineRunMetric,
    PipelineTaskMetric,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_run_metric(run_id: str = "run_collector_test") -> PipelineRunMetric:
    return PipelineRunMetric(
        dag_id="opspulse_pipeline",
        dag_run_id=run_id,
        batch_id="batch_collector_test",
        run_status="success",
        logical_date="2026-11-15T05:05:32+00:00",
        start_time="2026-11-15T05:28:21+00:00",
        end_time="2026-11-15T05:28:50+00:00",
        total_duration_seconds=29.0,
        successful_tasks=2,
        failed_tasks=0,
        skipped_tasks=0,
        retried_tasks=0,
        total_tasks=2,
    )


def _make_task_metrics(run_id: str = "run_collector_test"):
    return [
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=run_id,
            task_id="run_ingestion",
            task_state="success",
            start_time="2026-11-15T05:28:21+00:00",
            end_time="2026-11-15T05:28:25+00:00",
            duration_seconds=4.0,
        ),
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=run_id,
            task_id="transform_sales",
            task_state="success",
            start_time="2026-11-15T05:28:25+00:00",
            end_time="2026-11-15T05:28:30+00:00",
            duration_seconds=5.0,
        ),
    ]


def _make_failed_task_metrics(run_id: str = "run_collector_test"):
    return [
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=run_id,
            task_id="load_fact_sales",
            task_state="failed",
            start_time="2026-11-15T05:28:40+00:00",
            end_time="2026-11-15T05:28:42+00:00",
            duration_seconds=2.0,
            error_message="FK constraint violation",
        ),
    ]


# ---------------------------------------------------------------------------
# Full-stack mock patches
# ---------------------------------------------------------------------------

MOCK_TARGETS = {
    "get_airflow_engine": "monitoring.collector.get_airflow_metadata_engine",
    "reader_class": "monitoring.collector.AirflowMetadataReader",
    "volume_extractor": "monitoring.collector.extract_data_volume_metrics",
    "persist": "monitoring.collector.persist_observability_metrics",
    "save_reports": "monitoring.collector.save_monitoring_reports",
    "init_schema": "monitoring.collector.init_monitoring_schema",
    "get_db_engine": "monitoring.collector.get_database_engine",
}


def _build_mock_reader(run_id="run_collector_test"):
    mock_reader = MagicMock()
    run_metric = _make_run_metric(run_id)
    task_metrics = _make_task_metrics(run_id)
    mock_reader.build_run_metric.return_value = (run_metric, task_metrics)
    mock_reader.get_latest_dag_run.return_value = {"run_id": run_id}
    return mock_reader


class TestCollectObservabilitySuccess:
    """Happy-path tests for successful DAG runs."""

    def test_returns_observability_report(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]) as mock_ae, \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]) as mock_persist, \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            result = collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_test",
                project_root=tmp_path,
            )

        assert isinstance(result, PipelineObservabilityReport)
        assert result.dag_id == "opspulse_pipeline"

    def test_persist_called_once(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]) as mock_persist, \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_test",
                project_root=tmp_path,
            )

        mock_persist.assert_called_once()

    def test_no_persist_flag(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]) as mock_persist, \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_test",
                persist=False,
                project_root=tmp_path,
            )

        mock_persist.assert_not_called()

    def test_no_report_flag(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]) as mock_persist, \
             patch(MOCK_TARGETS["save_reports"]) as mock_save, \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_test",
                report=False,
                project_root=tmp_path,
            )

        mock_save.assert_not_called()

    def test_latest_run_resolved_when_no_run_id(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]), \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            collect_observability(dag_id="opspulse_pipeline", project_root=tmp_path)

        # get_latest_dag_run must have been called
        mock_reader.get_latest_dag_run.assert_called_once()


class TestFailureClassification:
    """Verify that failed tasks produce PipelineFailureEvent objects."""

    def _make_mock_reader_with_failure(self, run_id="run_collector_fail_test"):
        mock_reader = MagicMock()
        rm = PipelineRunMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=run_id,
            batch_id="batch_fail_test",
            run_status="failed",
            logical_date=None,
            start_time=None,
            end_time=None,
            total_duration_seconds=None,
            successful_tasks=1,
            failed_tasks=1,
        )
        task_metrics = [
            PipelineTaskMetric(
                dag_id="opspulse_pipeline",
                dag_run_id=run_id,
                task_id="load_fact_sales",
                task_state="failed",
                start_time=None,
                end_time=None,
                duration_seconds=None,
                error_message="FK violation",
            )
        ]
        mock_reader.build_run_metric.return_value = (rm, task_metrics)
        mock_reader.get_latest_dag_run.return_value = {"run_id": run_id}
        return mock_reader

    def test_failed_task_produces_failure_event(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = self._make_mock_reader_with_failure()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]), \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", return_value=MagicMock()):

            result = collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_fail_test",
                project_root=tmp_path,
            )

        assert len(result.failure_events) == 1
        fe = result.failure_events[0]
        assert fe.task_id == "load_fact_sales"
        assert fe.failure_category == FailureCategory.FACT_LOADING.value


class TestGracefulDegradation:
    """Warehouse DB errors must not crash the collector."""

    def test_warehouse_db_unavailable_continues(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = _build_mock_reader()

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader), \
             patch(MOCK_TARGETS["volume_extractor"], return_value=[]), \
             patch(MOCK_TARGETS["persist"]), \
             patch(MOCK_TARGETS["save_reports"], return_value=(tmp_path / "r.json", tmp_path / "r.csv")), \
             patch(MOCK_TARGETS["init_schema"]), \
             patch("monitoring.collector.get_database_engine", side_effect=RuntimeError("DB not available")):

            # Should not raise
            result = collect_observability(
                dag_id="opspulse_pipeline",
                dag_run_id="run_collector_test",
                project_root=tmp_path,
            )

        assert isinstance(result, PipelineObservabilityReport)

    def test_no_dag_runs_raises_runtime_error(self, tmp_path: Path):
        from monitoring.collector import collect_observability

        mock_reader = MagicMock()
        mock_reader.get_latest_dag_run.return_value = None

        with patch(MOCK_TARGETS["get_airflow_engine"]), \
             patch(MOCK_TARGETS["reader_class"], return_value=mock_reader):

            with pytest.raises(RuntimeError, match="No DAG runs found"):
                collect_observability(dag_id="opspulse_pipeline", project_root=tmp_path)
