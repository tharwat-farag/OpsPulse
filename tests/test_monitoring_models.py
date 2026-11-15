"""
Unit tests for monitoring.models — dataclasses and serialization.
"""

from datetime import datetime, timezone

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
# FailureCategory
# ---------------------------------------------------------------------------

class TestFailureCategory:
    def test_all_categories_are_strings(self):
        for cat in FailureCategory:
            assert isinstance(cat.value, str)

    def test_known_categories_exist(self):
        expected = {
            "Ingestion", "Transformation", "Data Quality",
            "Dimension Loading", "Bridge Loading", "Fact Loading",
            "Gold Validation", "Infrastructure / Database", "Unknown / Other",
        }
        actual = {cat.value for cat in FailureCategory}
        assert expected == actual


# ---------------------------------------------------------------------------
# PipelineRunMetric
# ---------------------------------------------------------------------------

class TestPipelineRunMetric:
    def _make(self, **kwargs):
        defaults = dict(
            dag_id="opspulse_pipeline",
            dag_run_id="manual__2026-11-15T05:05:32+00:00",
            batch_id="batch_20261115_051056_1d64c5da",
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
        defaults.update(kwargs)
        return PipelineRunMetric(**defaults)

    def test_creation(self):
        m = self._make()
        assert m.dag_id == "opspulse_pipeline"
        assert m.total_tasks == 30
        assert m.failed_tasks == 0

    def test_to_dict_has_all_keys(self):
        m = self._make()
        d = m.to_dict()
        assert "dag_id" in d
        assert "dag_run_id" in d
        assert "batch_id" in d
        assert "run_status" in d
        assert "total_duration_seconds" in d
        assert "collected_at" in d

    def test_collected_at_auto_set(self):
        m = self._make()
        # Should be a parseable ISO timestamp
        parsed = datetime.fromisoformat(m.collected_at)
        assert parsed is not None

    def test_optional_fields_can_be_none(self):
        m = self._make(batch_id=None, logical_date=None, start_time=None, end_time=None, total_duration_seconds=None)
        assert m.batch_id is None
        assert m.total_duration_seconds is None


# ---------------------------------------------------------------------------
# PipelineTaskMetric
# ---------------------------------------------------------------------------

class TestPipelineTaskMetric:
    def _make(self, **kwargs):
        defaults = dict(
            dag_id="opspulse_pipeline",
            dag_run_id="run_123",
            task_id="transform_sales",
            task_state="success",
            start_time="2026-11-15T05:28:25+00:00",
            end_time="2026-11-15T05:28:30+00:00",
            duration_seconds=5.1,
        )
        defaults.update(kwargs)
        return PipelineTaskMetric(**defaults)

    def test_creation(self):
        m = self._make()
        assert m.task_id == "transform_sales"
        assert m.duration_seconds == 5.1

    def test_defaults(self):
        m = self._make()
        assert m.try_number == 1
        assert m.max_retries == 0
        assert m.error_message is None
        assert m.historical_avg_duration_seconds is None
        assert m.duration_variance_pct is None

    def test_to_dict_round_trip(self):
        m = self._make(
            error_message="Some error",
            historical_avg_duration_seconds=4.5,
            duration_variance_pct=13.3,
        )
        d = m.to_dict()
        assert d["task_id"] == "transform_sales"
        assert d["error_message"] == "Some error"
        assert d["duration_variance_pct"] == 13.3


# ---------------------------------------------------------------------------
# PipelineDataVolumeMetric
# ---------------------------------------------------------------------------

class TestPipelineDataVolumeMetric:
    def test_creation(self):
        m = PipelineDataVolumeMetric(
            dag_run_id="run_123",
            batch_id="batch_abc",
            layer="Silver",
            metric_name="silver_valid_records",
            record_count=5000,
            metric_source="data/silver/batch_abc/*_manifest.json",
        )
        assert m.layer == "Silver"
        assert m.record_count == 5000

    def test_to_dict_has_layer(self):
        m = PipelineDataVolumeMetric(
            dag_run_id="r", batch_id="b", layer="Gold",
            metric_name="gold_records", record_count=37000,
            metric_source="postgresql:opspulse_dw.gold.*",
        )
        d = m.to_dict()
        assert d["layer"] == "Gold"
        assert d["record_count"] == 37000


# ---------------------------------------------------------------------------
# PipelineFailureEvent
# ---------------------------------------------------------------------------

class TestPipelineFailureEvent:
    def test_creation(self):
        fe = PipelineFailureEvent(
            dag_run_id="run_123",
            batch_id="batch_abc",
            task_id="transform_sales",
            failure_category=FailureCategory.TRANSFORMATION.value,
            error_type="ValueError",
            error_message="Unexpected null in amount column",
            failed_at="2026-11-15T05:28:30+00:00",
        )
        assert fe.failure_category == "Transformation"
        assert fe.error_type == "ValueError"

    def test_to_dict(self):
        fe = PipelineFailureEvent(
            dag_run_id="run_123",
            batch_id="batch_abc",
            task_id="load_fact_sales",
            failure_category=FailureCategory.FACT_LOADING.value,
            error_type="IntegrityError",
            error_message="FK violation",
            failed_at=None,
        )
        d = fe.to_dict()
        assert d["failure_category"] == "Fact Loading"
        assert d["failed_at"] is None


# ---------------------------------------------------------------------------
# PipelineObservabilityReport
# ---------------------------------------------------------------------------

class TestPipelineObservabilityReport:
    def _make_run_metric(self):
        return PipelineRunMetric(
            dag_id="opspulse_pipeline",
            dag_run_id="run_123",
            batch_id="batch_abc",
            run_status="success",
            logical_date=None,
            start_time=None,
            end_time=None,
            total_duration_seconds=29.0,
        )

    def test_empty_lists_default(self):
        rm = self._make_run_metric()
        obs = PipelineObservabilityReport(
            dag_id="opspulse_pipeline",
            dag_run_id="run_123",
            batch_id="batch_abc",
            collection_timestamp="2026-11-15T10:00:00+00:00",
            run_metric=rm,
        )
        assert obs.task_metrics == []
        assert obs.volume_metrics == []
        assert obs.failure_events == []

    def test_to_dict_structure(self):
        rm = self._make_run_metric()
        obs = PipelineObservabilityReport(
            dag_id="opspulse_pipeline",
            dag_run_id="run_123",
            batch_id="batch_abc",
            collection_timestamp="2026-11-15T10:00:00+00:00",
            run_metric=rm,
        )
        d = obs.to_dict()
        assert "run_metric" in d
        assert "task_metrics" in d
        assert "volume_metrics" in d
        assert "failure_events" in d
        assert isinstance(d["task_metrics"], list)
        assert isinstance(d["run_metric"], dict)
