"""
Unit tests for monitoring.volume_extractor — data volume metric extraction.
Tests read from real-structure synthetic files; never touch production DB.
"""

import json
from pathlib import Path

import pytest

from monitoring.volume_extractor import extract_data_volume_metrics


BATCH_ID = "batch_test_vol_001"
RUN_ID = "run_test_vol_001"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal synthetic project directory structure."""
    # Bronze manifest
    bronze_dir = tmp_path / "data" / "bronze" / BATCH_ID
    bronze_dir.mkdir(parents=True)
    _write_json(
        bronze_dir / "ingestion_manifest.json",
        {
            "batch_id": BATCH_ID,
            "total_records": 50000,
            "files_ingested": 12,
        },
    )

    # Silver manifests (3 datasets)
    silver_dir = tmp_path / "data" / "silver" / BATCH_ID
    silver_dir.mkdir(parents=True)
    for ds, (valid, quar) in [
        ("sales", (20000, 50)),
        ("inventory", (9000, 10)),
        ("products", (500, 0)),
    ]:
        _write_json(
            silver_dir / f"{ds}_manifest.json",
            {
                "dataset": ds,
                "batch_id": BATCH_ID,
                "silver_records": valid,
                "quarantined_records": quar,
            },
        )

    # DQ report
    dq_dir = tmp_path / "data" / "quality_reports"
    dq_dir.mkdir(parents=True)
    _write_json(
        dq_dir / "latest_quality_report.json",
        {
            "batch_id": BATCH_ID,
            "total_checks_executed": 210,
            "failed_checks": 0,
            "overall_score": 100.0,
        },
    )

    return tmp_path


class TestBronzeExtraction:
    def test_raw_records_extracted(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        raw = next((m for m in metrics if m.metric_name == "raw_records_ingested"), None)
        assert raw is not None
        assert raw.record_count == 50000
        assert raw.layer == "Raw"

    def test_bronze_records_extracted(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        bronze = next((m for m in metrics if m.metric_name == "bronze_records_stored"), None)
        assert bronze is not None
        assert bronze.record_count == 50000
        assert bronze.layer == "Bronze"


class TestSilverExtraction:
    def test_silver_valid_records_aggregated(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        silver = next((m for m in metrics if m.metric_name == "silver_valid_records"), None)
        assert silver is not None
        # 20000 + 9000 + 500 = 29500
        assert silver.record_count == 29500
        assert silver.layer == "Silver"

    def test_quarantine_records_aggregated(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        quar = next((m for m in metrics if m.metric_name == "silver_quarantined_records"), None)
        assert quar is not None
        # 50 + 10 + 0 = 60
        assert quar.record_count == 60


class TestDQExtraction:
    def test_dq_checks_extracted(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        dq = next((m for m in metrics if m.metric_name == "dq_checks_executed"), None)
        assert dq is not None
        assert dq.record_count == 210
        assert dq.layer == "DataQuality"

    def test_dq_failures_extracted(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        dqf = next((m for m in metrics if m.metric_name == "dq_checks_failed"), None)
        assert dqf is not None
        assert dqf.record_count == 0


class TestGracefulDegradation:
    def test_no_bronze_manifest_no_error(self, tmp_path: Path):
        """Missing bronze manifest does not crash — returns empty list."""
        metrics = extract_data_volume_metrics(
            batch_id="batch_nonexistent",
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=tmp_path,
        )
        # Should return an empty list without raising
        assert isinstance(metrics, list)

    def test_no_warehouse_engine_skips_gold(self, project_root: Path):
        """When warehouse_engine=None, Gold metrics are absent but no error raised."""
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        gold = [m for m in metrics if m.layer == "Gold"]
        assert gold == []

    def test_batch_id_propagated(self, project_root: Path):
        metrics = extract_data_volume_metrics(
            batch_id=BATCH_ID,
            dag_run_id=RUN_ID,
            warehouse_engine=None,
            project_root=project_root,
        )
        for m in metrics:
            assert m.batch_id == BATCH_ID
            assert m.dag_run_id == RUN_ID
