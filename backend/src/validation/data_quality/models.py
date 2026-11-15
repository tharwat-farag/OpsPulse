"""
OpsPulse Data Quality Framework - Structured Data Models.

Defines dataclasses and enums representing check results,
dataset summaries, and batch-level quality reports.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CheckCategory(str, Enum):
    COMPLETENESS = "Completeness"
    UNIQUENESS = "Uniqueness"
    REFERENTIAL_INTEGRITY = "Referential Integrity"
    BUSINESS_RULES = "Business Rules"
    VALIDITY = "Validity"


class CheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CheckSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class CheckResult:
    """
    Standard structured result model for every executed data quality check.
    Fully traceable to the specific dataset and batch.
    """
    dataset: str
    check_name: str
    check_category: str
    total_records: int
    passed_records: int
    failed_records: int
    quality_score: float
    status: str
    execution_timestamp: str
    batch_id: str
    severity: str = CheckSeverity.CRITICAL.value
    details: str = ""
    sample_failed_records: List[Any] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        dataset: str,
        check_name: str,
        category: CheckCategory,
        total_records: int,
        failed_records: int,
        batch_id: str,
        severity: CheckSeverity = CheckSeverity.CRITICAL,
        details: str = "",
        sample_failed_records: Optional[List[Any]] = None,
        timestamp: Optional[str] = None,
    ) -> "CheckResult":
        """Factory method to construct a CheckResult with automatic scoring."""
        if total_records < 0:
            total_records = 0
        if failed_records < 0:
            failed_records = 0
        if failed_records > total_records:
            failed_records = total_records

        passed_records = total_records - failed_records

        if total_records == 0:
            score = 100.0
            status_val = CheckStatus.PASSED.value
        else:
            score = round((passed_records / total_records) * 100.0, 2)
            if failed_records == 0:
                status_val = CheckStatus.PASSED.value
            elif severity == CheckSeverity.WARNING:
                status_val = CheckStatus.WARNING.value
            else:
                status_val = CheckStatus.FAILED.value

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        samples = (sample_failed_records or [])[:10]

        return cls(
            dataset=dataset,
            check_name=check_name,
            check_category=category.value,
            total_records=total_records,
            passed_records=passed_records,
            failed_records=failed_records,
            quality_score=score,
            status=status_val,
            execution_timestamp=ts,
            batch_id=batch_id,
            severity=severity.value,
            details=details,
            sample_failed_records=samples,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to clean dictionary representation."""
        data = asdict(self)
        return data


@dataclass
class DatasetQualitySummary:
    """Summary of data quality metrics for an individual dataset."""
    dataset: str
    total_records: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    quality_score: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchQualityReport:
    """Consolidated batch-level quality report containing all results."""
    batch_id: str
    execution_timestamp: str
    overall_quality_score: float
    total_checks_executed: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    status: str
    dataset_summaries: List[DatasetQualitySummary] = field(default_factory=list)
    dataset_failures: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    check_results: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "execution_timestamp": self.execution_timestamp,
            "overall_quality_score": self.overall_quality_score,
            "total_checks_executed": self.total_checks_executed,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "status": self.status,
            "dataset_summaries": [s.to_dict() for s in self.dataset_summaries],
            "dataset_failures": self.dataset_failures,
            "check_results": [r.to_dict() for r in self.check_results],
        }
