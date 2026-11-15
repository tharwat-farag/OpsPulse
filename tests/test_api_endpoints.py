"""
OpsPulse API Integration & Verification Tests.

Verifies FastAPI endpoints against live PostgreSQL opspulse_dw database.
Tests health check, aggregations, response structures, and pagination.
"""

import os
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check_returns_200_and_database_status(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["service"] == "opspulse-api"


class TestOverviewEndpoint:
    def test_get_overview_structure_and_data(self):
        response = client.get("/api/overview")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "revenueTrend" in data
        assert "branchPerformance" in data
        assert "channelShare" in data
        assert "topProducts" in data
        assert "latestRun" in data

        # Check KPI cards count
        assert len(data["kpis"]) == 6

        # Check Total Net Revenue is positive and non-zero
        rev_kpi = next(k for k in data["kpis"] if "Revenue" in k["title"])
        assert rev_kpi["numericValue"] > 300_000_000  # Real DB has $357M

        # Check 5 branches present in branchPerformance
        assert len(data["branchPerformance"]) == 5
        branch_names = {b["branchName"] for b in data["branchPerformance"]}
        assert "Mansoura Branch" in branch_names
        assert "Cairo Branch" in branch_names

        # Check 3 sales channels present
        assert len(data["channelShare"]) == 3
        channels = {c["channel"] for c in data["channelShare"]}
        assert "In-Store" in channels
        assert "Online" in channels
        assert "Phone" in channels

    def test_get_overview_quarterly_filter(self):
        response = client.get("/api/overview?year=2025&quarter=1")
        assert response.status_code == 200
        data = response.json()
        rev_kpi = next(k for k in data["kpis"] if "Revenue" in k["title"])
        assert "Q1 2025" in rev_kpi["title"]
        assert 80_000_000 < rev_kpi["numericValue"] < 95_000_000
        stockout_kpi = next(k for k in data["kpis"] if "Stockout" in k["title"])
        assert stockout_kpi["isPositive"] is True


class TestSalesEndpoints:
    def test_get_sales_summary(self):
        response = client.get("/api/sales")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "categoryShare" in data
        assert "transactions" in data
        assert len(data["kpis"]) == 6
        assert len(data["transactions"]) > 0

    def test_get_sales_quarterly_filter(self):
        response = client.get("/api/sales?year=2025&quarter=2")
        assert response.status_code == 200
        data = response.json()
        rev_kpi = next(k for k in data["kpis"] if "Gross Sales" in k["title"])
        assert "Q2 2025" in rev_kpi["title"]

    def test_get_sales_transactions_pagination(self):
        response = client.get("/api/sales/transactions?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pageSize" in data

        assert len(data["items"]) == 10
        assert data["total"] == 20000  # Exactly 20,000 sales lines in DB
        assert data["page"] == 1
        assert data["pageSize"] == 10

    def test_sales_transactions_channel_filter(self):
        response = client.get("/api/sales/transactions?channel=Online&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6564  # Real DB Online channel count
        for item in data["items"]:
            assert item["channel"] == "Online"

    def test_sales_transactions_search(self):
        response = client.get("/api/sales/transactions?search=Mansoura&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert "Mansoura" in item["branch"]


class TestInventoryEndpoints:
    def test_get_inventory_summary(self):
        response = client.get("/api/inventory")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "warehouses" in data
        assert "items" in data

        # Check 3 warehouses present
        assert len(data["warehouses"]) == 3
        wh_names = {w["warehouseName"] for w in data["warehouses"]}
        assert "Cairo Main Warehouse" in wh_names
        assert "Alexandria Main Warehouse" in wh_names
        assert "Giza Main Warehouse" in wh_names

    def test_get_inventory_items_pagination_and_status(self):
        response = client.get("/api/inventory/items?page=1&page_size=15&status=out_of_stock")
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["status"] == "out_of_stock"


class TestProcurementEndpoints:
    def test_get_procurement_summary(self):
        response = client.get("/api/procurement")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "statusBreakdown" in data
        assert "purchaseOrders" in data

        # Check PO status categories
        statuses = {s["status"] for s in data["statusBreakdown"]}
        assert "Fully Received" in statuses
        assert "Partially Received" in statuses

    def test_get_procurement_orders_pagination(self):
        response = client.get("/api/procurement/orders?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1000  # Exactly 1,000 unique POs in DB
        assert len(data["items"]) == 10


class TestSuppliersEndpoint:
    def test_get_suppliers(self):
        response = client.get("/api/suppliers")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "directory" in data
        assert len(data["directory"]) == 10  # 10 suppliers in DB

        supp_names = [s["supplierName"] for s in data["directory"]]
        assert "Sullivan, Stewart and Price" in supp_names


class TestExpensesEndpoint:
    def test_get_expenses(self):
        response = client.get("/api/expenses")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "categories" in data
        assert "monthlyTrend" in data
        assert "expenses" in data

        # 5 categories
        assert len(data["categories"]) == 5
        cat_names = {c["category"] for c in data["categories"]}
        assert "Salaries" in cat_names
        assert "Rent" in cat_names
        assert "Transportation" in cat_names


class TestMonitoringEndpoint:
    def test_get_monitoring(self):
        response = client.get("/api/monitoring")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "volumeLineage" in data
        assert "taskMetrics" in data
        assert "runHistory" in data

        # 30 tasks from Airflow DAG
        assert len(data["taskMetrics"]) == 30

        # Volume lineage contains Medallion layers
        layers = {v["layer"] for v in data["volumeLineage"]}
        assert "Raw" in layers
        assert "Bronze" in layers
        assert "Silver" in layers
        assert "Gold" in layers


class TestDataQualityEndpoint:
    def test_get_data_quality(self):
        response = client.get("/api/data-quality")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert "summary" in data
        assert "checkDetails" in data

        # 210 checks
        assert data["summary"]["checksExecuted"] == 210
        assert data["summary"]["overallScore"] == 100.0
