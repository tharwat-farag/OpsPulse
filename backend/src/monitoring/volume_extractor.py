"""
OpsPulse Pipeline Observability - Data Volume Metric Extractor.

Extracts authoritative record counts across Medallion layers:
- Raw / Bronze records from Bronze ingestion manifests
- Silver and Quarantine records from Silver transformation manifests
- Gold table row counts from warehouse database queries
- Data Quality check counts from quality reports
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import PipelineDataVolumeMetric

PROJECT_ROOT = Path(__file__).resolve().parents[3]

GOLD_TABLES = [
    "dim_date",
    "dim_product",
    "dim_customer",
    "dim_branch",
    "dim_supplier",
    "dim_warehouse",
    "dim_sales_channel",
    "dim_expense_category",
    "bridge_branch_warehouse",
    "bridge_product_supplier",
    "fact_sales",
    "fact_inventory_snapshot",
    "fact_operating_expenses",
    "fact_purchase_order_lines",
    "fact_goods_receipts",
]


def extract_data_volume_metrics(
    batch_id: str,
    dag_run_id: str,
    warehouse_engine: Optional[Engine] = None,
    project_root: Optional[Path] = None,
) -> List[PipelineDataVolumeMetric]:
    """
    Extracts authoritative record counts across all layers for the specified batch.
    Never guesses or manufactures metrics.
    """
    metrics: List[PipelineDataVolumeMetric] = []
    root = project_root or PROJECT_ROOT

    # 1. Bronze & Raw Volumes from Ingestion Manifest
    bronze_manifest_path = root / "data" / "bronze" / batch_id / "ingestion_manifest.json"
    if bronze_manifest_path.exists():
        try:
            with open(bronze_manifest_path, "r", encoding="utf-8") as f:
                b_manifest = json.load(f)
            total_ingested = b_manifest.get("total_records", 0)

            metrics.append(
                PipelineDataVolumeMetric(
                    dag_run_id=dag_run_id,
                    batch_id=batch_id,
                    layer="Raw",
                    metric_name="raw_records_ingested",
                    record_count=int(total_ingested),
                    metric_source=f"data/bronze/{batch_id}/ingestion_manifest.json",
                )
            )
            metrics.append(
                PipelineDataVolumeMetric(
                    dag_run_id=dag_run_id,
                    batch_id=batch_id,
                    layer="Bronze",
                    metric_name="bronze_records_stored",
                    record_count=int(total_ingested),
                    metric_source=f"data/bronze/{batch_id}/ingestion_manifest.json",
                )
            )
        except Exception as exc:
            print(f"[Warning] Error reading bronze ingestion manifest: {exc}")

    # 2. Silver & Quarantine Volumes from Silver Manifests
    silver_batch_dir = root / "data" / "silver" / batch_id
    if silver_batch_dir.exists():
        total_silver = 0
        total_quarantine = 0
        found_manifests = 0

        for manifest_file in silver_batch_dir.glob("*_manifest.json"):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    s_manifest = json.load(f)
                valid = s_manifest.get("silver_records", s_manifest.get("valid_records", 0))
                quar = s_manifest.get("quarantined_records", 0)
                total_silver += int(valid)
                total_quarantine += int(quar)
                found_manifests += 1
            except Exception:
                pass

        if found_manifests > 0:
            metrics.append(
                PipelineDataVolumeMetric(
                    dag_run_id=dag_run_id,
                    batch_id=batch_id,
                    layer="Silver",
                    metric_name="silver_valid_records",
                    record_count=total_silver,
                    metric_source=f"data/silver/{batch_id}/*_manifest.json",
                )
            )
            metrics.append(
                PipelineDataVolumeMetric(
                    dag_run_id=dag_run_id,
                    batch_id=batch_id,
                    layer="Quarantine",
                    metric_name="silver_quarantined_records",
                    record_count=total_quarantine,
                    metric_source=f"data/silver/{batch_id}/*_manifest.json",
                )
            )

    # 3. Gold Warehouse Volumes
    if warehouse_engine:
        try:
            with warehouse_engine.connect() as conn:
                total_gold = 0
                for table in GOLD_TABLES:
                    count_val = conn.execute(
                        text(f"SELECT COUNT(*) FROM gold.{table}")
                    ).scalar() or 0
                    total_gold += int(count_val)

                metrics.append(
                    PipelineDataVolumeMetric(
                        dag_run_id=dag_run_id,
                        batch_id=batch_id,
                        layer="Gold",
                        metric_name="gold_warehouse_records",
                        record_count=total_gold,
                        metric_source="postgresql:opspulse_dw.gold.*",
                    )
                )
        except Exception as exc:
            print(f"[Warning] Could not query Gold warehouse row counts: {exc}")

    # 4. Data Quality Metrics from DQ Report
    clean_batch = batch_id.replace("/", "_").replace("\\", "_")
    dq_report_path = root / "data" / "quality_reports" / f"quality_report_{clean_batch}.json"
    if not dq_report_path.exists():
        dq_report_path = root / "data" / "quality_reports" / "latest_quality_report.json"

    if dq_report_path.exists():
        try:
            with open(dq_report_path, "r", encoding="utf-8") as f:
                dq_data = json.load(f)
            
            # Verify batch matches or is current
            if dq_data.get("batch_id") == batch_id:
                metrics.append(
                    PipelineDataVolumeMetric(
                        dag_run_id=dag_run_id,
                        batch_id=batch_id,
                        layer="DataQuality",
                        metric_name="dq_checks_executed",
                        record_count=int(dq_data.get("total_checks_executed", 0)),
                        metric_source=str(dq_report_path.name),
                    )
                )
                metrics.append(
                    PipelineDataVolumeMetric(
                        dag_run_id=dag_run_id,
                        batch_id=batch_id,
                        layer="DataQuality",
                        metric_name="dq_checks_failed",
                        record_count=int(dq_data.get("failed_checks", 0)),
                        metric_source=str(dq_report_path.name),
                    )
                )
        except Exception as exc:
            print(f"[Warning] Could not read DQ report: {exc}")

    return metrics
