"""
OpsPulse Pipeline Observability - Failure Analytics & Classification.

Classifies task failures based on pipeline stage, task identity,
exception type, and diagnostic error signatures.
"""

import re
from typing import Optional, Tuple
from .models import FailureCategory

# Known infrastructure or database error keywords
INFRASTRUCTURE_PATTERNS = [
    r"connection\s+refused",
    r"could\s+not\s+connect\s+to\s+server",
    r"operationalerror",
    r"timed?\s*out",
    r"out\s+of\s+memory",
    r"disk\s+full",
    r"no\s+space\s+left\s+on\s+device",
    r"deadlock\s+detected",
    r"canceling\s+statement\s+due\s+to\s+statement\s+timeout",
    r"psycopg\..*operational",
    r"connection\s+reset\s+by\s+peer",
]


def classify_task_failure(
    task_id: str,
    error_message: Optional[str] = None,
    exception_type: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Classifies a task failure into a standardized FailureCategory and extracts
    the representative error type.

    Returns:
        Tuple of (failure_category, error_type)
    """
    msg_lower = (error_message or "").lower()
    exc_type = exception_type or "UnknownError"

    # 1. Check for infrastructure/database level failure across any task
    for pattern in INFRASTRUCTURE_PATTERNS:
        if re.search(pattern, msg_lower) or (exception_type and re.search(pattern, exception_type.lower())):
            return FailureCategory.INFRASTRUCTURE_DATABASE.value, exc_type

    # 2. Stage-based classification by task_id
    if task_id == "run_ingestion":
        return FailureCategory.INGESTION.value, exc_type

    if task_id.startswith("transform_"):
        return FailureCategory.TRANSFORMATION.value, exc_type

    if task_id in ("audit_silver_layer", "validate_data_quality"):
        return FailureCategory.DATA_QUALITY.value, exc_type

    if task_id.startswith("load_dim_"):
        return FailureCategory.DIMENSION_LOADING.value, exc_type

    if task_id.startswith("load_bridge_"):
        return FailureCategory.BRIDGE_LOADING.value, exc_type

    if task_id.startswith("load_fact_"):
        return FailureCategory.FACT_LOADING.value, exc_type

    if task_id in ("validate_gold_warehouse", "validate_date_dimension"):
        return FailureCategory.GOLD_VALIDATION.value, exc_type

    return FailureCategory.UNKNOWN.value, exc_type
