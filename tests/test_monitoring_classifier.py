"""
Unit tests for monitoring.classifier — task failure classification.
"""

import pytest

from monitoring.classifier import classify_task_failure
from monitoring.models import FailureCategory


class TestClassifyByTaskId:
    """Stage-based classification via task_id."""

    def test_ingestion_task(self):
        cat, _ = classify_task_failure("run_ingestion")
        assert cat == FailureCategory.INGESTION.value

    def test_transform_task(self):
        cat, _ = classify_task_failure("transform_sales")
        assert cat == FailureCategory.TRANSFORMATION.value

    def test_transform_another(self):
        cat, _ = classify_task_failure("transform_inventory")
        assert cat == FailureCategory.TRANSFORMATION.value

    def test_audit_silver_layer(self):
        cat, _ = classify_task_failure("audit_silver_layer")
        assert cat == FailureCategory.DATA_QUALITY.value

    def test_validate_data_quality(self):
        cat, _ = classify_task_failure("validate_data_quality")
        assert cat == FailureCategory.DATA_QUALITY.value

    def test_dim_loading(self):
        cat, _ = classify_task_failure("load_dim_customer")
        assert cat == FailureCategory.DIMENSION_LOADING.value

    def test_dim_loading_product(self):
        cat, _ = classify_task_failure("load_dim_product")
        assert cat == FailureCategory.DIMENSION_LOADING.value

    def test_bridge_loading(self):
        cat, _ = classify_task_failure("load_bridge_product_supplier")
        assert cat == FailureCategory.BRIDGE_LOADING.value

    def test_fact_loading(self):
        cat, _ = classify_task_failure("load_fact_sales")
        assert cat == FailureCategory.FACT_LOADING.value

    def test_fact_loading_inventory(self):
        cat, _ = classify_task_failure("load_fact_inventory_snapshot")
        assert cat == FailureCategory.FACT_LOADING.value

    def test_validate_gold_warehouse(self):
        cat, _ = classify_task_failure("validate_gold_warehouse")
        assert cat == FailureCategory.GOLD_VALIDATION.value

    def test_validate_date_dimension(self):
        cat, _ = classify_task_failure("validate_date_dimension")
        assert cat == FailureCategory.GOLD_VALIDATION.value

    def test_unknown_task(self):
        cat, _ = classify_task_failure("some_random_task")
        assert cat == FailureCategory.UNKNOWN.value

    def test_collect_pipeline_observability_is_unknown(self):
        # The observability task itself has no special classification
        cat, _ = classify_task_failure("collect_pipeline_observability")
        assert cat == FailureCategory.UNKNOWN.value


class TestInfrastructureOverride:
    """Infrastructure errors should override stage classification."""

    def test_connection_refused_overrides_transform(self):
        cat, _ = classify_task_failure(
            "transform_sales",
            error_message="Connection refused while connecting to PostgreSQL",
        )
        assert cat == FailureCategory.INFRASTRUCTURE_DATABASE.value

    def test_timeout_overrides_dim_load(self):
        cat, _ = classify_task_failure(
            "load_dim_product",
            error_message="Query timed out after 30 seconds",
        )
        assert cat == FailureCategory.INFRASTRUCTURE_DATABASE.value

    def test_out_of_memory_overrides_ingestion(self):
        cat, _ = classify_task_failure(
            "run_ingestion",
            error_message="Killed: out of memory",
        )
        assert cat == FailureCategory.INFRASTRUCTURE_DATABASE.value

    def test_deadlock_overrides_fact(self):
        cat, _ = classify_task_failure(
            "load_fact_sales",
            error_message="deadlock detected on table fact_sales",
        )
        assert cat == FailureCategory.INFRASTRUCTURE_DATABASE.value

    def test_operational_error_in_exception_type(self):
        cat, _ = classify_task_failure(
            "run_ingestion",
            exception_type="OperationalError",
        )
        assert cat == FailureCategory.INFRASTRUCTURE_DATABASE.value

    def test_no_error_message_uses_task_id(self):
        cat, _ = classify_task_failure("transform_products", error_message=None)
        assert cat == FailureCategory.TRANSFORMATION.value


class TestErrorTypePassthrough:
    """Error type should reflect exception_type or fall back to 'UnknownError'."""

    def test_no_exception_type_returns_unknown_error(self):
        _, err_type = classify_task_failure("transform_sales")
        assert err_type == "UnknownError"

    def test_exception_type_returned_as_is(self):
        _, err_type = classify_task_failure("transform_sales", exception_type="ValueError")
        assert err_type == "ValueError"

    def test_infrastructure_still_returns_exception_type(self):
        _, err_type = classify_task_failure(
            "run_ingestion",
            error_message="connection refused",
            exception_type="psycopg.OperationalError",
        )
        assert err_type == "psycopg.OperationalError"
