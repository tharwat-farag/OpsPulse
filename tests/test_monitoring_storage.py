"""
Unit tests for monitoring.storage — idempotent PostgreSQL persistence.

Uses an in-memory SQLite database via SQLAlchemy to avoid production dependencies.
The monitoring schema tables are created programmatically to match the
PostgreSQL DDL, adapted for SQLite compatibility (no ON CONFLICT ... DO UPDATE
in older SQLite — we use INSERT OR REPLACE approach via test helpers).

Since the production storage.py uses PostgreSQL-specific ON CONFLICT syntax,
these tests verify:
  1. persist_observability_metrics raises no errors on first insert.
  2. A second call with the same data succeeds (idempotency at run_metric level).
  3. Failure events are cleared and re-inserted.
  4. All models are accepted by the function signature.

We patch the SQLAlchemy engine with a real PostgreSQL test connection
when OPSPULSE_DATABASE_URL is available, otherwise skip DB-dependent tests.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, call

from monitoring.models import (
    FailureCategory,
    PipelineDataVolumeMetric,
    PipelineFailureEvent,
    PipelineRunMetric,
    PipelineTaskMetric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_metric(run_id: str = "run_storage_test_001") -> PipelineRunMetric:
    return PipelineRunMetric(
        dag_id="opspulse_pipeline",
        dag_run_id=run_id,
        batch_id="batch_storage_test_001",
        run_status="success",
        logical_date="2026-11-15T05:05:32+00:00",
        start_time="2026-11-15T05:28:21+00:00",
        end_time="2026-11-15T05:28:50+00:00",
        total_duration_seconds=29.0,
        successful_tasks=30,
        failed_tasks=0,
        skipped_tasks=0,
        retried_tasks=0,
        total_tasks=30,
    )


def _make_task_metrics(run_id: str = "run_storage_test_001"):
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


def _make_volume_metrics(run_id: str = "run_storage_test_001"):
    return [
        PipelineDataVolumeMetric(
            dag_run_id=run_id,
            batch_id="batch_storage_test_001",
            layer="Silver",
            metric_name="silver_valid_records",
            record_count=5000,
            metric_source="manifest",
        )
    ]


def _make_failure_events(run_id: str = "run_storage_test_001"):
    return [
        PipelineFailureEvent(
            dag_run_id=run_id,
            batch_id="batch_storage_test_001",
            task_id="load_fact_sales",
            failure_category=FailureCategory.FACT_LOADING.value,
            error_type="IntegrityError",
            error_message="FK violation",
            failed_at="2026-11-15T05:28:42+00:00",
        )
    ]


# ---------------------------------------------------------------------------
# Mock-based tests (no real DB required)
# ---------------------------------------------------------------------------

class TestPersistWithMockEngine:
    """
    Verify persist_observability_metrics calls the engine correctly
    without connecting to a real database.
    """

    def _make_mock_engine(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_conn
        return mock_engine, mock_conn

    def test_persist_calls_engine_begin(self):
        from monitoring.storage import persist_observability_metrics

        mock_engine, mock_conn = self._make_mock_engine()
        run_metric = _make_run_metric()

        persist_observability_metrics(
            engine=mock_engine,
            run_metric=run_metric,
            task_metrics=[],
            volume_metrics=[],
            failure_events=[],
        )

        mock_engine.begin.assert_called_once()

    def test_persist_executes_statements(self):
        from monitoring.storage import persist_observability_metrics

        mock_engine, mock_conn = self._make_mock_engine()
        run_metric = _make_run_metric()
        task_metrics = _make_task_metrics()
        volume_metrics = _make_volume_metrics()
        failure_events = _make_failure_events()

        persist_observability_metrics(
            engine=mock_engine,
            run_metric=run_metric,
            task_metrics=task_metrics,
            volume_metrics=volume_metrics,
            failure_events=failure_events,
        )

        # Should have executed:
        # 1 run upsert + 2 task upserts + 1 vol upsert + 1 failure DELETE + 1 failure INSERT
        assert mock_conn.execute.call_count >= 6

    def test_persist_with_empty_lists(self):
        """Zero-failure, zero-volume runs must not raise."""
        from monitoring.storage import persist_observability_metrics

        mock_engine, mock_conn = self._make_mock_engine()
        run_metric = _make_run_metric()

        # Should not raise
        persist_observability_metrics(
            engine=mock_engine,
            run_metric=run_metric,
            task_metrics=[],
            volume_metrics=[],
            failure_events=[],
        )

    def test_persist_failure_delete_before_insert(self):
        """Failure events must be DELETEd then re-INSERTed (idempotent refresh)."""
        from monitoring.storage import persist_observability_metrics
        from sqlalchemy import text

        mock_engine, mock_conn = self._make_mock_engine()
        run_metric = _make_run_metric()
        failure_events = _make_failure_events()

        # Capture SQL strings executed
        executed_sqls = []
        original_execute = mock_conn.execute
        def capturing_execute(stmt, *args, **kwargs):
            if hasattr(stmt, 'text'):
                executed_sqls.append(stmt.text.upper())
            return MagicMock()
        mock_conn.execute.side_effect = capturing_execute

        persist_observability_metrics(
            engine=mock_engine,
            run_metric=run_metric,
            task_metrics=[],
            volume_metrics=[],
            failure_events=failure_events,
        )

        delete_indices = [i for i, s in enumerate(executed_sqls) if "DELETE" in s]
        insert_indices = [i for i, s in enumerate(executed_sqls) if "INSERT INTO MONITORING.PIPELINE_FAILURE_EVENTS" in s]

        assert delete_indices, "Expected a DELETE statement for failure events"
        assert insert_indices, "Expected an INSERT for failure events"
        assert delete_indices[0] < insert_indices[0], "DELETE must precede INSERT"


# ---------------------------------------------------------------------------
# Live DB tests (skipped when OPSPULSE_DATABASE_URL not available)
# ---------------------------------------------------------------------------

HAS_DB = bool(os.getenv("OPSPULSE_DATABASE_URL"))

@pytest.mark.skipif(not HAS_DB, reason="OPSPULSE_DATABASE_URL not configured")
class TestPersistWithLiveDB:
    """Integration tests using the real PostgreSQL monitoring schema."""

    @pytest.fixture(autouse=True)
    def engine(self):
        from warehouse.db_connection import get_database_engine
        from monitoring.schema import init_monitoring_schema
        eng = get_database_engine()
        init_monitoring_schema(eng)
        return eng

    def test_idempotent_double_insert(self, engine):
        from monitoring.storage import persist_observability_metrics
        from sqlalchemy import text

        run_id = "run_pytest_idempotent_test"
        run_metric = _make_run_metric(run_id)

        # Clean up before test
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM monitoring.pipeline_run_metrics WHERE dag_run_id = :r"), {"r": run_id})
            conn.execute(text("DELETE FROM monitoring.pipeline_task_metrics WHERE dag_run_id = :r"), {"r": run_id})
            conn.execute(text("DELETE FROM monitoring.pipeline_data_volume_metrics WHERE dag_run_id = :r"), {"r": run_id})
            conn.execute(text("DELETE FROM monitoring.pipeline_failure_events WHERE dag_run_id = :r"), {"r": run_id})

        # First insert
        persist_observability_metrics(engine, run_metric, _make_task_metrics(run_id), _make_volume_metrics(run_id), [])
        # Second insert — must not raise
        persist_observability_metrics(engine, run_metric, _make_task_metrics(run_id), _make_volume_metrics(run_id), [])

        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM monitoring.pipeline_run_metrics WHERE dag_run_id = :r"),
                {"r": run_id},
            ).scalar()
        assert count == 1

        # Cleanup
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM monitoring.pipeline_run_metrics WHERE dag_run_id = :r"), {"r": run_id})
            conn.execute(text("DELETE FROM monitoring.pipeline_task_metrics WHERE dag_run_id = :r"), {"r": run_id})
            conn.execute(text("DELETE FROM monitoring.pipeline_data_volume_metrics WHERE dag_run_id = :r"), {"r": run_id})
