-- OpsPulse Pipeline Observability & Run Analytics Schema
-- Step 1: Create monitoring schema and tables

CREATE SCHEMA IF NOT EXISTS monitoring;

-- 1. Pipeline Run Metrics: Overall execution metrics per DAG run
CREATE TABLE IF NOT EXISTS monitoring.pipeline_run_metrics (
    run_metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    dag_run_id VARCHAR(255) NOT NULL,
    batch_id VARCHAR(100),
    run_status VARCHAR(50) NOT NULL,
    logical_date TIMESTAMPTZ,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    total_duration_seconds NUMERIC(10, 2),
    successful_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    skipped_tasks INTEGER NOT NULL DEFAULT 0,
    retried_tasks INTEGER NOT NULL DEFAULT 0,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_run UNIQUE (dag_id, dag_run_id)
);

CREATE INDEX IF NOT EXISTS idx_run_metrics_dag_run ON monitoring.pipeline_run_metrics (dag_run_id);
CREATE INDEX IF NOT EXISTS idx_run_metrics_batch ON monitoring.pipeline_run_metrics (batch_id);
CREATE INDEX IF NOT EXISTS idx_run_metrics_start ON monitoring.pipeline_run_metrics (start_time);
CREATE INDEX IF NOT EXISTS idx_run_metrics_status ON monitoring.pipeline_run_metrics (run_status);

-- 2. Pipeline Task Metrics: Individual task execution telemetry
CREATE TABLE IF NOT EXISTS monitoring.pipeline_task_metrics (
    task_metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    dag_run_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    task_state VARCHAR(50),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_seconds NUMERIC(10, 3),
    try_number INTEGER DEFAULT 1,
    max_retries INTEGER DEFAULT 0,
    error_message TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_task_metric UNIQUE (dag_run_id, task_id),
    CONSTRAINT fk_task_run FOREIGN KEY (dag_id, dag_run_id) 
        REFERENCES monitoring.pipeline_run_metrics (dag_id, dag_run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_metrics_run ON monitoring.pipeline_task_metrics (dag_run_id);
CREATE INDEX IF NOT EXISTS idx_task_metrics_task ON monitoring.pipeline_task_metrics (task_id);
CREATE INDEX IF NOT EXISTS idx_task_metrics_state ON monitoring.pipeline_task_metrics (task_state);

-- 3. Pipeline Data Volume Metrics: Multi-layer record volumes per batch/run
CREATE TABLE IF NOT EXISTS monitoring.pipeline_data_volume_metrics (
    volume_metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dag_run_id VARCHAR(255) NOT NULL,
    batch_id VARCHAR(100) NOT NULL,
    layer VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    record_count BIGINT NOT NULL,
    metric_source VARCHAR(255) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_volume_metric UNIQUE (dag_run_id, batch_id, layer, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_volume_metrics_run ON monitoring.pipeline_data_volume_metrics (dag_run_id);
CREATE INDEX IF NOT EXISTS idx_volume_metrics_batch ON monitoring.pipeline_data_volume_metrics (batch_id);
CREATE INDEX IF NOT EXISTS idx_volume_metrics_layer ON monitoring.pipeline_data_volume_metrics (layer);

-- 4. Pipeline Failure Events: Classified operational failure diagnostics
CREATE TABLE IF NOT EXISTS monitoring.pipeline_failure_events (
    failure_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dag_run_id VARCHAR(255) NOT NULL,
    batch_id VARCHAR(100),
    task_id VARCHAR(100) NOT NULL,
    failure_category VARCHAR(100) NOT NULL,
    error_type VARCHAR(255),
    error_message TEXT,
    failed_at TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_failure_events_run ON monitoring.pipeline_failure_events (dag_run_id);
CREATE INDEX IF NOT EXISTS idx_failure_events_category ON monitoring.pipeline_failure_events (failure_category);
CREATE INDEX IF NOT EXISTS idx_failure_events_task ON monitoring.pipeline_failure_events (task_id);
