# OpsPulse — Day 8: Production Observability & Pipeline Run Analytics

## 1. Overview & Architectural Objectives

OpsPulse Day 8 implements an enterprise-grade **Pipeline Observability & Run Analytics Layer** directly integrated with Apache Airflow 3.4.0 and the PostgreSQL Data Warehouse (`opspulse_dw`).

The primary goal of Day 8 is to provide operational visibility and business monitoring on top of the Medallion architecture (Bronze -> Silver -> Gold), capturing end-to-end execution telemetry, data volume lineage, failure classifications, and task duration variances without duplicating features native to Airflow or mixing operational telemetry into analytical business tables.

### Key Architectural Tenets
1. **Separation of Concerns**: Airflow metadata (`airflow_metadata`) is strictly read-only. Analytical operational monitoring data is stored in a dedicated `monitoring` schema within the data warehouse (`opspulse_dw`).
2. **Idempotence**: Every telemetry collection step can be run repeatedly for any DAG run or batch without generating duplicate records or corrupted state (`ON CONFLICT ... DO UPDATE`).
3. **No Credential Exposure**: Database connection strings are resolved dynamically from environment variables (`OPSPULSE_DATABASE_URL`, `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`) without hardcoded secrets.
4. **Resilience**: The collector continues even if optional layers (e.g., Gold warehouse during an early-stage failure) are unreachable.
5. **Airflow 3.4.0 Native Compatibility**: Handles Airflow 3 database schema constructs (including `xcom_v2`) and integrates as an `ALL_DONE` terminal task.

---

## 2. Telemetry Architecture

```mermaid
flowchart TD
    subgraph Airflow["Apache Airflow 3.4.0 (WSL)"]
        AF_DAG["opspulse_pipeline DAG"]
        AF_META[("airflow_metadata DB<br/>dag_run, task_instance, xcom_v2")]
    end

    subgraph Collector["Observability Collection Engine"]
        READER["AirflowMetadataReader<br/>(Read-Only Extraction)"]
        VOL_EXT["VolumeExtractor<br/>(Bronze, Silver, Gold, DQ)"]
        CLASSIFIER["FailureClassifier<br/>(Stage & Pattern Detection)"]
        STORAGE["PostgreSQL Storage<br/>(Idempotent Upsert)"]
        REPORTER["Report Generator<br/>(JSON & CSV Artifacts)"]
    end

    subgraph StorageTarget["PostgreSQL Warehouse (opspulse_dw)"]
        SCH_MON["monitoring Schema"]
        T_RUN["monitoring.pipeline_run_metrics"]
        T_TASK["monitoring.pipeline_task_metrics"]
        T_VOL["monitoring.pipeline_data_volume_metrics"]
        T_FAIL["monitoring.pipeline_failure_events"]
    end

    subgraph FileOutputs["Artifacts & Reports"]
        JSON_OUT["data/monitoring_reports/*.json"]
        CSV_OUT["data/monitoring_reports/*.csv"]
    end

    AF_DAG -->|Triggers at completion| READER
    AF_META -.->|Read-Only Queries| READER
    READER --> COLLECTOR_CORE["collect_observability()"]
    VOL_EXT --> COLLECTOR_CORE
    CLASSIFIER --> COLLECTOR_CORE
    COLLECTOR_CORE --> STORAGE
    COLLECTOR_CORE --> REPORTER

    STORAGE --> T_RUN
    STORAGE --> T_TASK
    STORAGE --> T_VOL
    STORAGE --> T_FAIL

    REPORTER --> JSON_OUT
    REPORTER --> CSV_OUT
```

---

## 3. Database Schema Design (`monitoring`)

A dedicated schema `monitoring` was established in `opspulse_dw` to house normalized run analytics.

### Table: `monitoring.pipeline_run_metrics`
Tracks high-level execution telemetry per DAG run.

| Column | Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | Primary Key |
| `dag_id` | `VARCHAR(250)` | Airflow DAG Identifier |
| `dag_run_id` | `VARCHAR(250)` | Unique DAG Run ID (Unique with `dag_id`) |
| `batch_id` | `VARCHAR(100)` | OpsPulse Ingestion/Processing Batch ID |
| `run_status` | `VARCHAR(50)` | Final DAG Run State (`success`, `failed`) |
| `logical_date` | `TIMESTAMPTZ` | Airflow Logical Execution Date |
| `start_time` | `TIMESTAMPTZ` | Run start timestamp |
| `end_time` | `TIMESTAMPTZ` | Run end timestamp |
| `total_duration_seconds` | `NUMERIC(10,2)` | Run duration in seconds |
| `successful_tasks` | `INTEGER` | Count of successful task instances |
| `failed_tasks` | `INTEGER` | Count of failed task instances |
| `skipped_tasks` | `INTEGER` | Count of skipped task instances |
| `retried_tasks` | `INTEGER` | Count of retried task instances |
| `total_tasks` | `INTEGER` | Total tasks executed in the run |
| `collected_at` | `TIMESTAMPTZ` | Timestamp when metrics were collected |

### Table: `monitoring.pipeline_task_metrics`
Tracks task-level granular telemetry and historical comparison.

| Column | Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | Primary Key |
| `dag_id` | `VARCHAR(250)` | Airflow DAG Identifier |
| `dag_run_id` | `VARCHAR(250)` | Unique DAG Run ID |
| `task_id` | `VARCHAR(250)` | Unique Task ID within DAG (Unique with `dag_run_id`) |
| `task_state` | `VARCHAR(50)` | Task State (`success`, `failed`, `skipped`, etc.) |
| `start_time` | `TIMESTAMPTZ` | Task instance start timestamp |
| `end_time` | `TIMESTAMPTZ` | Task instance end timestamp |
| `duration_seconds` | `NUMERIC(10,3)` | Task instance execution duration in seconds |
| `try_number` | `INTEGER` | Attempt number for this run |
| `max_retries` | `INTEGER` | Configured maximum retries |
| `error_message` | `TEXT` | Extracted error diagnostic summary (for failures) |
| `collected_at` | `TIMESTAMPTZ` | Timestamp when metrics were collected |

### Table: `monitoring.pipeline_data_volume_metrics`
Measures data volume changes across the Medallion architectural layers.

| Column | Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | Primary Key |
| `dag_run_id` | `VARCHAR(250)` | Unique DAG Run ID |
| `batch_id` | `VARCHAR(100)` | Associated OpsPulse Batch ID |
| `layer` | `VARCHAR(50)` | Layer (`Raw`, `Bronze`, `Silver`, `Quarantine`, `Gold`, `DataQuality`) |
| `metric_name` | `VARCHAR(100)` | Specific volume metric name |
| `record_count` | `BIGINT` | Authoritative record count |
| `metric_source` | `VARCHAR(255)` | Audit source path or origin |
| `collected_at` | `TIMESTAMPTZ` | Timestamp when metrics were collected |

*Unique constraint: `(dag_run_id, batch_id, layer, metric_name)`*

### Table: `monitoring.pipeline_failure_events`
Stores classified failure diagnoses when errors occur.

| Column | Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | Primary Key |
| `dag_run_id` | `VARCHAR(250)` | Associated DAG Run ID |
| `batch_id` | `VARCHAR(100)` | Associated Batch ID (if resolved) |
| `task_id` | `VARCHAR(250)` | Failed Task Identifier |
| `failure_category` | `VARCHAR(100)` | Categorized Failure Stage/Domain |
| `error_type` | `VARCHAR(100)` | Python/SQL Exception Class |
| `error_message` | `TEXT` | Diagnostic error details |
| `failed_at` | `TIMESTAMPTZ` | Failure occurrence timestamp |
| `collected_at` | `TIMESTAMPTZ` | Timestamp when metric was logged |

---

## 4. Failure Classification Engine

Task failures are classified via `monitoring.classifier.classify_task_failure` into standard operational categories:

1. **Infrastructure / Database**: Overrides task identity when error signatures match connectivity, timeout, OOM, disk, or deadlock conditions:
   - Regex patterns: `connection\s+refused`, `could\s+not\s+connect`, `operationalerror`, `timed?\s*out`, `out\s+of\s+memory`, `deadlock\s+detected`, `psycopg\..*operational`.
2. **Ingestion**: Failures occurring in `run_ingestion`.
3. **Transformation**: Failures in any `transform_*` tasks.
4. **Data Quality**: Failures in `audit_silver_layer` or `validate_data_quality`.
5. **Dimension Loading**: Failures in any `load_dim_*` tasks.
6. **Bridge Loading**: Failures in any `load_bridge_*` tasks.
7. **Fact Loading**: Failures in any `load_fact_*` tasks.
8. **Gold Validation**: Failures in `validate_gold_warehouse` or `validate_date_dimension`.
9. **Unknown / Other**: Unclassified anomalies.

---

## 5. Authoritative Data Volume Lineage

The volume extractor retrieves authoritative counts across pipeline stages:
- **Raw / Bronze**: Extracted from `data/bronze/<batch_id>/ingestion_manifest.json` (`total_records`).
- **Silver & Quarantine**: Aggregated across all 12 dataset manifests in `data/silver/<batch_id>/*_manifest.json` (`silver_records` / `valid_records` and `quarantined_records`).
- **Gold Warehouse**: Queried directly from `gold.*` tables in `opspulse_dw` across all 15 dimensional, bridge, and fact tables.
- **Data Quality**: Extracted from `data/quality_reports/quality_report_<batch_id>.json` (`total_checks_executed` and `failed_checks`).

### Verified Volume Baseline (Batch `batch_20261115_051056_1d64c5da`)
- **Raw Records Ingested**: `37,721`
- **Bronze Records Stored**: `37,721`
- **Silver Valid Records**: `37,721`
- **Quarantined Records**: `0`
- **Gold Warehouse Records**: `37,464`
- **Data Quality Checks**: `210` executed, `0` failed (100% pass rate)

---

## 6. Airflow DAG Integration

The production DAG (`opspulse_pipeline`) integrates the observability collection via an `@task` decorated function with `trigger_rule=TriggerRule.ALL_DONE`.

```python
from airflow.sdk import dag, task
from airflow.task.trigger_rule import TriggerRule

@task(task_id="collect_pipeline_observability", trigger_rule=TriggerRule.ALL_DONE)
def collect_pipeline_observability(**context):
    from monitoring.collector import collect_observability

    dag_run_id = context["run_id"]
    result = collect_observability(
        dag_id="opspulse_pipeline",
        dag_run_id=dag_run_id,
        persist=True,
        report=True,
    )
    return {
        "dag_run_id": result.dag_run_id,
        "batch_id": result.batch_id,
        "tasks_collected": len(result.task_metrics),
        "volume_metrics_collected": len(result.volume_metrics),
        "failure_events": len(result.failure_events),
    }

observability_task = collect_pipeline_observability()
final_validation >> observability_task
```

### DAG Task Flow
1. `run_ingestion`
2. Parallel 12 Silver transformation tasks (`transform_*`)
3. `audit_silver_layer` & `validate_data_quality` (parallel quality gates)
4. Dimension & Bridge loaders (`load_dim_*`, `load_bridge_*`) & `validate_date_dimension`
5. Fact loaders (`load_fact_*`)
6. `validate_gold_warehouse`
7. **`collect_pipeline_observability`** (runs regardless of upstream pass/fail)

---

## 7. CLI & Module Execution

The observability module can be run from the command line against any existing or latest DAG run:

```bash
# Run against latest DAG run
python backend/src/monitoring/runner.py --dag-id opspulse_pipeline

# Run against a specific historical run
python backend/src/monitoring/runner.py --dag-id opspulse_pipeline --dag-run-id "manual__2026-11-15T05:05:32.814530+00:00"

# Dry-run (generate reports only, skip database persistence)
python backend/src/monitoring/runner.py --no-persist
```

Reports are written to:
- `data/monitoring_reports/monitoring_report_<run_id>.json`
- `data/monitoring_reports/monitoring_report_<run_id>.csv`
- Symlinks / alias files: `data/monitoring_reports/latest_monitoring_report.json` and `.csv`

---

## 8. Verification & Test Suite

The test suite covers models, classification rules, volume extraction, database persistence, report generation, and full collector orchestration.

### Test Execution Summary
- **Total Test Cases**: `105 passed`
  - Day 7 Data Quality Tests: `36 passed`
  - Day 8 Monitoring Models Tests: `12 passed`
  - Day 8 Classifier Tests: `23 passed`
  - Day 8 Volume Extractor Tests: `7 passed`
  - Day 8 Storage Persistence Tests: `5 passed`
  - Day 8 Report Generator Tests: `9 passed`
  - Day 8 Collector Orchestrator Tests: `8 passed`
  - Other core validation/business rule tests: `5 passed`
- **Execution Time**: `~1.8 seconds`
- **Pass Rate**: `100%`

```powershell
$env:OPSPULSE_DATABASE_URL="postgresql+psycopg://retailflow_admin:111111@127.0.0.1:5432/opspulse_dw"
$env:PYTHONPATH="backend/src"
.\.venv\Scripts\pytest.exe -v
```
