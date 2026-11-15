"""
OpsPulse Pipeline Observability & Run Analytics - Structured Data Models.

Defines dataclasses for pipeline run telemetry, task performance metrics,
data volume measurements, failure events, and consolidated observability reports.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureCategory(str, Enum):
    INGESTION = "Ingestion"
    TRANSFORMATION = "Transformation"
    DATA_QUALITY = "Data Quality"
    DIMENSION_LOADING = "Dimension Loading"
    BRIDGE_LOADING = "Bridge Loading"
    FACT_LOADING = "Fact Loading"
    GOLD_VALIDATION = "Gold Validation"
    INFRASTRUCTURE_DATABASE = "Infrastructure / Database"
    UNKNOWN = "Unknown / Other"


@dataclass
class PipelineRunMetric:
    """Consolidated metrics for an individual DAG run."""
    dag_id: str
    dag_run_id: str
    batch_id: Optional[str]
    run_status: str
    logical_date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    total_duration_seconds: Optional[float]
    successful_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    retried_tasks: int = 0
    total_tasks: int = 0
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineTaskMetric:
    """Performance telemetry for a single task instance."""
    dag_id: str
    dag_run_id: str
    task_id: str
    task_state: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]
    try_number: int = 1
    max_retries: int = 0
    error_message: Optional[str] = None
    historical_avg_duration_seconds: Optional[float] = None
    duration_variance_pct: Optional[float] = None
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineDataVolumeMetric:
    """Record volume measurement across architectural layers."""
    dag_run_id: str
    batch_id: str
    layer: str  # Raw, Bronze, Silver, Quarantine, Gold, DataQuality
    metric_name: str
    record_count: int
    metric_source: str  # manifest, audit_silver_layer, dq_report, database_gold
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineFailureEvent:
    """Classified failure diagnosis event for failed tasks."""
    dag_run_id: str
    batch_id: Optional[str]
    task_id: str
    failure_category: str
    error_type: Optional[str]
    error_message: Optional[str]
    failed_at: Optional[str]
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineObservabilityReport:
    """Complete observability report for a specific pipeline execution."""
    dag_id: str
    dag_run_id: str
    batch_id: Optional[str]
    collection_timestamp: str
    run_metric: PipelineRunMetric
    task_metrics: List[PipelineTaskMetric] = field(default_factory=list)
    volume_metrics: List[PipelineDataVolumeMetric] = field(default_factory=list)
    failure_events: List[PipelineFailureEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "dag_run_id": self.dag_run_id,
            "batch_id": self.batch_id,
            "collection_timestamp": self.collection_timestamp,
            "run_metric": self.run_metric.to_dict(),
            "task_metrics": [t.to_dict() for t in self.task_metrics],
            "volume_metrics": [v.to_dict() for v in self.volume_metrics],
            "failure_events": [f.to_dict() for f in self.failure_events],
        }
