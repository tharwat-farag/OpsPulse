"""
Unit tests for monitoring.reporter — JSON and CSV report generation.
"""

import csv
import json
from pathlib import Path

import pytest

from monitoring.models import (
    PipelineDataVolumeMetric,
    PipelineFailureEvent,
    PipelineObservabilityReport,
    PipelineRunMetric,
    PipelineTaskMetric,
    FailureCategory,
)
from monitoring.reporter import save_monitoring_reports


def _build_sample_report(dag_run_id: str = "run_test_001") -> PipelineObservabilityReport:
    run_metric = PipelineRunMetric(
        dag_id="opspulse_pipeline",
        dag_run_id=dag_run_id,
        batch_id="batch_test_001",
        run_status="success",
        logical_date="2026-11-15T05:05:32+00:00",
        start_time="2026-11-15T05:28:21+00:00",
        end_time="2026-11-15T05:28:50+00:00",
        total_duration_seconds=29.0,
        successful_tasks=3,
        failed_tasks=0,
        skipped_tasks=0,
        retried_tasks=0,
        total_tasks=3,
    )
    task_metrics = [
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=dag_run_id,
            task_id="run_ingestion",
            task_state="success",
            start_time="2026-11-15T05:28:21+00:00",
            end_time="2026-11-15T05:28:25+00:00",
            duration_seconds=4.0,
            try_number=1,
            max_retries=0,
            historical_avg_duration_seconds=3.8,
            duration_variance_pct=5.26,
        ),
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=dag_run_id,
            task_id="transform_sales",
            task_state="success",
            start_time="2026-11-15T05:28:25+00:00",
            end_time="2026-11-15T05:28:30+00:00",
            duration_seconds=5.0,
            try_number=1,
            max_retries=0,
        ),
        PipelineTaskMetric(
            dag_id="opspulse_pipeline",
            dag_run_id=dag_run_id,
            task_id="load_fact_sales",
            task_state="failed",
            start_time="2026-11-15T05:28:40+00:00",
            end_time="2026-11-15T05:28:42+00:00",
            duration_seconds=2.0,
            try_number=2,
            max_retries=1,
            error_message="FK constraint violation on dim_product_key",
        ),
    ]
    volume_metrics = [
        PipelineDataVolumeMetric(
            dag_run_id=dag_run_id,
            batch_id="batch_test_001",
            layer="Silver",
            metric_name="silver_valid_records",
            record_count=5000,
            metric_source="manifest",
        )
    ]
    failure_events = [
        PipelineFailureEvent(
            dag_run_id=dag_run_id,
            batch_id="batch_test_001",
            task_id="load_fact_sales",
            failure_category=FailureCategory.FACT_LOADING.value,
            error_type="IntegrityError",
            error_message="FK constraint violation on dim_product_key",
            failed_at="2026-11-15T05:28:42+00:00",
        )
    ]
    return PipelineObservabilityReport(
        dag_id="opspulse_pipeline",
        dag_run_id=dag_run_id,
        batch_id="batch_test_001",
        collection_timestamp="2026-11-15T10:00:00+00:00",
        run_metric=run_metric,
        task_metrics=task_metrics,
        volume_metrics=volume_metrics,
        failure_events=failure_events,
    )


class TestSaveMonitoringReports:
    def test_creates_json_and_csv(self, tmp_path: Path):
        report = _build_sample_report()
        json_path, csv_path = save_monitoring_reports(report, output_dir=tmp_path)

        assert json_path.exists()
        assert csv_path.exists()

    def test_json_is_valid(self, tmp_path: Path):
        report = _build_sample_report()
        json_path, _ = save_monitoring_reports(report, output_dir=tmp_path)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["dag_id"] == "opspulse_pipeline"
        assert data["batch_id"] == "batch_test_001"
        assert "run_metric" in data
        assert "task_metrics" in data
        assert len(data["task_metrics"]) == 3

    def test_json_contains_failure_events(self, tmp_path: Path):
        report = _build_sample_report()
        json_path, _ = save_monitoring_reports(report, output_dir=tmp_path)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["failure_events"]) == 1
        assert data["failure_events"][0]["failure_category"] == "Fact Loading"

    def test_csv_has_expected_rows(self, tmp_path: Path):
        report = _build_sample_report()
        _, csv_path = save_monitoring_reports(report, output_dir=tmp_path)

        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        # 3 task metrics → 3 CSV rows
        assert len(rows) == 3

    def test_csv_headers(self, tmp_path: Path):
        report = _build_sample_report()
        _, csv_path = save_monitoring_reports(report, output_dir=tmp_path)

        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        required_headers = [
            "dag_id", "dag_run_id", "batch_id", "task_id",
            "task_state", "duration_seconds", "error_message",
        ]
        for h in required_headers:
            assert h in headers, f"Missing CSV header: {h}"

    def test_csv_error_message_populated(self, tmp_path: Path):
        report = _build_sample_report()
        _, csv_path = save_monitoring_reports(report, output_dir=tmp_path)

        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        failed_row = next(r for r in rows if r["task_id"] == "load_fact_sales")
        assert "FK constraint violation" in failed_row["error_message"]

    def test_latest_symlinks_created(self, tmp_path: Path):
        report = _build_sample_report()
        save_monitoring_reports(report, output_dir=tmp_path)

        assert (tmp_path / "latest_monitoring_report.json").exists()
        assert (tmp_path / "latest_monitoring_report.csv").exists()

    def test_idempotent_overwrite(self, tmp_path: Path):
        report = _build_sample_report()
        json1, csv1 = save_monitoring_reports(report, output_dir=tmp_path)
        json2, csv2 = save_monitoring_reports(report, output_dir=tmp_path)

        # Same paths both times
        assert json1 == json2
        assert csv1 == csv2
        # Files still valid JSON
        with open(json2, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["dag_id"] == "opspulse_pipeline"

    def test_run_id_special_chars_sanitized(self, tmp_path: Path):
        """Run IDs with colons/plus signs must not break the filename."""
        report = _build_sample_report(dag_run_id="manual__2026-11-15T05:05:32.814530+00:00")
        json_path, csv_path = save_monitoring_reports(report, output_dir=tmp_path)

        assert ":" not in json_path.name
        assert "+" not in json_path.name
