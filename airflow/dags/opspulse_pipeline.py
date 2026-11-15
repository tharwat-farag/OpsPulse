
import importlib
import sys
from pathlib import Path
from datetime import datetime

from airflow.sdk import dag, task
from airflow.task.trigger_rule import TriggerRule
from sqlalchemy import inspect, text

PROJECT_SRC = Path(
    "/mnt/d/Data Engineer Projects/OpsPulse/backend/src"
)

if not PROJECT_SRC.exists():
    raise FileNotFoundError(
        f"Project source directory not found: {PROJECT_SRC}"
    )

sys.path.insert(0, str(PROJECT_SRC))


@task
def run_ingestion() -> str:
    module = importlib.import_module(
        "ingestion.ingest_raw_to_bronze"
    )

    batch_id = module.main()

    if not batch_id:
        raise RuntimeError("Ingestion did not return a batch_id.")

    print(f"Created batch: {batch_id}")
    return batch_id


@task
def run_batch_module(module_name: str, batch_id: str):
    module = importlib.import_module(module_name)
    result = module.main(batch_id)

    print(f"Completed: {module_name}")
    return result


@task
def run_noarg_module(module_name: str, function_name: str):
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)

    result = function()

    print(f"Completed: {module_name}.{function_name}")
    return result


@task
def validate_date_dimension():
    from warehouse.db_connection import get_database_engine

    engine = get_database_engine()

    try:
        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM gold.dim_date")
            ).scalar_one()

        if count == 0:
            raise RuntimeError(
                "gold.dim_date is empty. Fact loading cannot continue."
            )

        print(f"Date dimension records: {count:,}")

    finally:
        engine.dispose()


@task
def validate_gold_warehouse():
    from warehouse.db_connection import get_database_engine

    required_tables = [
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

    engine = get_database_engine()

    try:
        inspector = inspect(engine)
        existing_tables = set(
            inspector.get_table_names(schema="gold")
        )

        missing = sorted(set(required_tables) - existing_tables)

        if missing:
            raise RuntimeError(
                f"Missing Gold tables: {missing}"
            )

        with engine.connect() as connection:
            for table in required_tables:
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM gold.{table}")
                ).scalar_one()

                print(f"gold.{table}: {count:,} rows")

        print("Gold warehouse validation passed.")

    finally:
        engine.dispose()


@dag(
    dag_id="opspulse_pipeline",
    description="OpsPulse end-to-end data engineering pipeline with Data Quality Gate",
    start_date=datetime(2026, 11, 13),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["opspulse", "data-engineering", "etl", "data-quality"],
)
def opspulse_pipeline():

    # 1. Raw to Bronze
    batch_id = run_ingestion()

    # 2. Bronze to Silver transformations
    transform_modules = {
        "branches": "transformation.transform_branches_to_silver",
        "customers": "transformation.transform_customers_to_silver",
        "goods_receipts": "transformation.transform_goods_receipts_to_silver",
        "inventory": "transformation.transform_inventory_to_silver",
        "operating_expenses": "transformation.transform_operating_expenses_to_silver",
        "product_suppliers": "transformation.transform_product_suppliers_to_silver",
        "products": "transformation.transform_products_to_silver",
        "purchase_order_lines": "transformation.transform_purchase_order_lines_to_silver",
        "purchase_orders": "transformation.transform_purchase_orders_to_silver",
        "sales": "transformation.transform_sales_to_silver",
        "suppliers": "transformation.transform_suppliers_to_silver",
        "warehouses": "transformation.transform_warehouses_to_silver",
    }

    transforms = {
        name: run_batch_module.override(
            task_id=f"transform_{name}"
        )(module_name, batch_id)
        for name, module_name in transform_modules.items()
    }

    # Transformation dependencies
    transforms["products"] >> transforms["product_suppliers"]
    transforms["suppliers"] >> transforms["product_suppliers"]

    transforms["suppliers"] >> transforms["purchase_orders"]

    transforms["purchase_orders"] >> transforms["purchase_order_lines"]
    transforms["products"] >> transforms["purchase_order_lines"]

    transforms["purchase_order_lines"] >> transforms["goods_receipts"]
    transforms["purchase_orders"] >> transforms["goods_receipts"]

    transforms["products"] >> transforms["inventory"]
    transforms["warehouses"] >> transforms["inventory"]

    transforms["products"] >> transforms["sales"]
    transforms["customers"] >> transforms["sales"]
    transforms["branches"] >> transforms["sales"]

    transforms["branches"] >> transforms["operating_expenses"]

    # 3. Silver audit (Manifest and record reconciliation)
    silver_audit = run_batch_module.override(
        task_id="audit_silver_layer"
    )(
        "validation.audit_silver_layer",
        batch_id,
    )

    for transform_task in transforms.values():
        transform_task >> silver_audit

    # 3b. Automated Data Quality Gate (Completeness, Uniqueness, Referential, Business Rules, Validity)
    data_quality_gate = run_batch_module.override(
        task_id="validate_data_quality"
    )(
        "validation.data_quality.runner",
        batch_id,
    )

    silver_audit >> data_quality_gate

    # 4. Dimensions
    dimension_modules = {
        "dim_branch": "warehouse.loaders.load_dim_branch",
        "dim_customer": "warehouse.loaders.load_dim_customer",
        "dim_product": "warehouse.loaders.load_dim_product",
        "dim_supplier": "warehouse.loaders.load_dim_supplier",
        "dim_warehouse": "warehouse.loaders.load_dim_warehouse",
        "dim_sales_channel": "warehouse.loaders.load_dim_sales_channel",
        "dim_expense_category": "warehouse.loaders.load_dim_expense_category",
    }

    dimensions = {
        name: run_batch_module.override(
            task_id=f"load_{name}"
        )(module_name, batch_id)
        for name, module_name in dimension_modules.items()
    }

    for dimension_task in dimensions.values():
        data_quality_gate >> dimension_task

    # 5. Date dimension validation
    date_check = validate_date_dimension()
    data_quality_gate >> date_check

    # 6. Bridges
    branch_warehouse_bridge = run_noarg_module.override(
        task_id="load_bridge_branch_warehouse"
    )(
        "warehouse.loaders.load_bridge_branch_warehouse",
        "load_bridge_branch_warehouse",
    )

    product_supplier_bridge = run_batch_module.override(
        task_id="load_bridge_product_supplier"
    )(
        "warehouse.loaders.load_bridge_product_supplier",
        batch_id,
    )

    dimensions["dim_branch"] >> branch_warehouse_bridge
    dimensions["dim_warehouse"] >> branch_warehouse_bridge

    dimensions["dim_product"] >> product_supplier_bridge
    dimensions["dim_supplier"] >> product_supplier_bridge

    # 7. Fact tables
    sales_fact = run_batch_module.override(
        task_id="load_fact_sales"
    )(
        "warehouse.loaders.load_fact_sales",
        batch_id,
    )

    inventory_fact = run_batch_module.override(
        task_id="load_fact_inventory_snapshot"
    )(
        "warehouse.loaders.load_fact_inventory_snapshot",
        batch_id,
    )

    expenses_fact = run_batch_module.override(
        task_id="load_fact_operating_expenses"
    )(
        "warehouse.loaders.load_fact_operating_expenses",
        batch_id,
    )

    purchase_lines_fact = run_batch_module.override(
        task_id="load_fact_purchase_order_lines"
    )(
        "warehouse.loaders.load_fact_purchase_order_lines",
        batch_id,
    )

    goods_receipts_fact = run_batch_module.override(
        task_id="load_fact_goods_receipts"
    )(
        "warehouse.loaders.load_fact_goods_receipts",
        batch_id,
    )

    # Sales dependencies
    dimensions["dim_product"] >> sales_fact
    dimensions["dim_customer"] >> sales_fact
    dimensions["dim_branch"] >> sales_fact
    dimensions["dim_sales_channel"] >> sales_fact
    date_check >> sales_fact

    # Inventory dependencies
    dimensions["dim_product"] >> inventory_fact
    dimensions["dim_warehouse"] >> inventory_fact
    date_check >> inventory_fact

    # Operating expenses dependencies
    dimensions["dim_branch"] >> expenses_fact
    dimensions["dim_expense_category"] >> expenses_fact
    date_check >> expenses_fact

    # Purchase order lines dependencies
    dimensions["dim_product"] >> purchase_lines_fact
    dimensions["dim_supplier"] >> purchase_lines_fact
    date_check >> purchase_lines_fact

    # Goods receipts must wait for purchase order lines
    purchase_lines_fact >> goods_receipts_fact
    dimensions["dim_product"] >> goods_receipts_fact
    dimensions["dim_supplier"] >> goods_receipts_fact
    date_check >> goods_receipts_fact

    # 8. Final Gold validation
    final_validation = validate_gold_warehouse()

    for fact_task in [
        sales_fact,
        inventory_fact,
        expenses_fact,
        purchase_lines_fact,
        goods_receipts_fact,
    ]:
        fact_task >> final_validation

    branch_warehouse_bridge >> final_validation
    product_supplier_bridge >> final_validation

    # 9. Pipeline Observability — runs regardless of upstream success/failure
    @task(task_id="collect_pipeline_observability", trigger_rule=TriggerRule.ALL_DONE)
    def collect_pipeline_observability(**context):
        """
        Collects pipeline run telemetry after all other tasks complete.
        Uses trigger_rule=ALL_DONE so failure data is captured too.
        """
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


opspulse_pipeline()
