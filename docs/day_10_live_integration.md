# OpsPulse — Day 10: Live Data Integration & Backend API

## 1. Overview & Architectural Objectives

OpsPulse Day 10 concludes the development lifecycle by transforming OpsPulse from a dashboard presenting static mock data into a **fully integrated, data-connected enterprise business operations intelligence platform**.

The frontend (Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts) now directly queries a high-performance **FastAPI backend** (`backend/src/api/`), which executes optimized analytical SQL queries against the **PostgreSQL Data Warehouse** (`opspulse_dw`), specifically targeting the `gold`, `monitoring`, and `quality_reports` data assets established across Days 1 through 8.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             OpsPulse Architecture                           │
└─────────────────────────────────────────────────────────────────────────────┘
  ┌────────────────────────┐         ┌────────────────────────┐
  │  Next.js 14 Frontend   │  HTTP   │  FastAPI Backend API   │
  │   (Port 3000 / App)    │ ◄─────► │   (Port 8000 / Uvicorn)│
  │  lib/api/client.ts     │  JSON   │   backend/src/api/     │
  └────────────────────────┘         └───────────┬────────────┘
                                                 │
                                                 │ SQLAlchemy / psycopg
                                                 ▼
                                     ┌────────────────────────┐
                                     │ PostgreSQL Warehouse   │
                                     │     (opspulse_dw)      │
                                     │  • gold.*              │
                                     │  • monitoring.*        │
                                     │  • quality_reports     │
                                     └────────────────────────┘
```

### Core Principles Maintained
1. **Zero Aesthetic or Layout Drift**:
   - The executive UI design, color tokens, responsive sidebar/header, Recharts visualizers, and interactive tables created in Day 9 are preserved verbatim.
2. **Production-Grade Security**:
   - Database credentials, connection strings, and secrets reside strictly on the server side (`OPSPULSE_DATABASE_URL`). The frontend only exposes `NEXT_PUBLIC_API_URL`.
3. **Data Authenticity**:
   - All KPIs, trends, tables, and distribution charts reflect genuine transactional and operational aggregates from calendar year 2025 in `opspulse_dw`. No numbers are fabricated or hardcoded.
4. **Resilient UX**:
   - Every page features unified loading skeletons (`LoadingSkeleton`), live error alerts (`AlertTriangle` banner with retry trigger), and graceful empty states.

---

## 2. Directory Structure

```text
backend/src/api/
├── __init__.py                 # API package initialization
├── database.py                 # SQLAlchemy engine management & health checks
├── main.py                     # FastAPI application, CORS, error handling, health
└── routes/
    ├── __init__.py
    ├── data_quality.py         # /api/data-quality (Day 7 DQ report mirror)
    ├── expenses.py             # /api/expenses (OpEx KPIs, ledger, monthly variance)
    ├── inventory.py            # /api/inventory (SKU health, warehouses, snapshots)
    ├── monitoring.py           # /api/monitoring (Day 8 pipeline telemetry & lineage)
    ├── overview.py             # /api/overview (Executive summary KPIs & velocity)
    ├── procurement.py          # /api/procurement (PO orders, receipts, lead times)
    ├── sales.py                # /api/sales (Revenue KPIs, transactions, channel share)
    └── suppliers.py            # /api/suppliers (Vendor scorecard, OTIF, risk levels)

frontend/
├── .env.local                  # NEXT_PUBLIC_API_URL=http://localhost:8000/api
├── lib/
│   └── api/
│       └── client.ts           # Strongly typed API client & pagination support
└── app/
    ├── page.tsx                # Overview Dashboard connected to live API
    ├── sales/page.tsx          # Sales Analytics connected to live API
    ├── inventory/page.tsx      # Inventory Health connected to live API
    ├── procurement/page.tsx    # Procurement Tracking connected to live API
    ├── suppliers/page.tsx      # Supplier Scorecards connected to live API
    ├── expenses/page.tsx       # Expense Ledger connected to live API
    ├── monitoring/page.tsx     # Airflow Pipeline Observability connected to live API
    ├── data-quality/page.tsx   # Automated Data Quality Gates connected to live API
    └── settings/page.tsx       # System Diagnostics & Live DB Health Check

tests/
├── conftest.py                 # Pytest fixtures and fallback OPSPULSE_DATABASE_URL
└── test_api_endpoints.py       # 14 FastAPI integration and endpoint tests
```

---

## 3. Backend API Endpoints & Data Model Mapping

| Method | Endpoint | Query Parameters | Underlying DW Schemas & Tables | Output Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | None | `opspulse_dw` (SELECT 1) | Service health, DB connectivity status, and server timestamp. |
| `GET` | `/api/overview` | None | `gold.fact_sales`, `dim_branch`, `dim_sales_channel`, `dim_product`, `monitoring.pipeline_runs` | Executive KPIs (Net Revenue, Profit, Orders, Inventory Value, Stockout Rate, Open POs), revenue trend, branch performance, channel mix, top 5 products, latest DAG run. |
| `GET` | `/api/sales` | None | `gold.fact_sales`, `dim_sales_channel`, `dim_product` | Sales domain KPIs (Net Revenue, Gross Margin, Average Order Value, Total Units), monthly sales trend, channel distribution, top products. |
| `GET` | `/api/sales/transactions` | `page`, `page_size`, `channel`, `branch`, `search` | `gold.fact_sales`, `dim_customer`, `dim_branch`, `dim_sales_channel` | Paginated sales transactions with customer names, branch locations, channel types, units, and net amounts. |
| `GET` | `/api/inventory` | None | `gold.fact_inventory_snapshot`, `dim_product`, `dim_warehouse` | Inventory KPIs (Total Valuation, Total Units, Low Stock Alert Count, Out of Stock Count), warehouse valuation distribution, category stock distribution. |
| `GET` | `/api/inventory/items` | `page`, `page_size`, `warehouse`, `status`, `search` | `gold.fact_inventory_snapshot`, `dim_product`, `dim_warehouse` | Paginated SKU snapshots with warehouse name, reorder point, current quantity, valuation, and calculated stock status (`In Stock`, `Low Stock`, `Out of Stock`). |
| `GET` | `/api/procurement` | None | `gold.fact_purchase_order_lines`, `fact_goods_receipts`, `dim_supplier` | Procurement KPIs (Total Committed Spend, Total POs, Received Lines, Open Lines, On-Time Delivery Rate), monthly purchasing trend, supplier spend share. |
| `GET` | `/api/procurement/orders` | `page`, `page_size`, `status`, `supplier`, `search` | `gold.fact_purchase_order_lines`, `fact_goods_receipts`, `dim_supplier` | Paginated purchase orders with line counts, ordered quantity, received quantity, total spend, and fulfillment status (`Completed`, `Partial`, `Open`). |
| `GET` | `/api/suppliers` | None | `gold.dim_supplier`, `fact_purchase_order_lines`, `fact_goods_receipts` | Supplier domain KPIs (Active Suppliers, Preferred Suppliers, Total Spend, Average Rating), full vendor scorecard directory with spend, OTIF rate, and risk tiering. |
| `GET` | `/api/expenses` | None | `gold.fact_operating_expenses`, `dim_expense_category`, `dim_branch` | Expense KPIs (Total OpEx, Average Monthly Run Rate, Active Cost Centers, Expense Categories), category breakdown, monthly expense curve, complete expense ledger. |
| `GET` | `/api/monitoring` | None | `monitoring.pipeline_runs`, `pipeline_task_metrics`, `pipeline_dataset_lineage` | Day 8 production observability mirror: latest Airflow 3.4.0 DAG runs, duration telemetry, task duration/status table, Medallion volume lineage (Bronze -> Silver -> Gold). |
| `GET` | `/api/data-quality` | None | `data/quality_reports/latest_quality_report.json` | Day 7 automated quality framework mirror: 210 checks across 12 Silver datasets, category breakdown (Completeness, Uniqueness, Validity, Referential, Business Rules), failing records log. |

---

## 4. Key Metric Calculations & Warehouse Reconciliation

All business calculations derive directly from the validated Gold schema in `opspulse_dw`:

### 1. Sales & Profitability
- **Total Net Revenue**:
  $$\text{Net Revenue} = \sum \text{net\_amount} = \$357,406,606.39$$
  *(Over 20,000 transaction rows and 8,053 unique orders in `gold.fact_sales`).*
- **Gross Profit & Margin**:
  $$\text{Gross Profit} = \sum (\text{net\_amount} - (\text{quantity} \times \text{standard\_cost})) = \$45,419,252.39 \quad (12.71\%)$$
- **Average Order Value (AOV)**:
  $$\text{AOV} = \frac{\$357,406,606.39}{8,053} = \$44,381.79$$

### 2. Inventory Health
- **Total Inventory Valuation**:
  $$\text{Inventory Value} = \sum (\text{quantity\_on\_hand} \times \text{standard\_cost}) = \$14,926,929.50$$
  *(Calculated across the latest snapshot date for 9,000 SKU-warehouse records).*
- **Stockout Rate**:
  $$\text{Stockout Rate} = \frac{\text{SKUs with } \text{quantity\_on\_hand} = 0}{\text{Total Active SKUs}} = 0.0\%$$
- **Active Warehouses**:
  - `Cairo Main Warehouse` (4,498,400 units, \$4.98M value)
  - `Giza Main Warehouse` (4,510,720 units, \$4.98M value)
  - `Alexandria Main Warehouse` (4,500,520 units, \$4.97M value)

### 3. Procurement & Spend
- **Committed PO Spend**:
  $$\text{Total Spend} = \sum (\text{ordered\_quantity} \times \text{unit\_cost}) = \$2,999,999.00$$
  *(Across 1,000 POs and 3,000 lines in `gold.fact_purchase_order_lines`).*
- **Receipt Reconciliation**:
  - Received Lines: 1,453 lines in `gold.fact_goods_receipts`
  - Open Lines: 1,547 lines awaiting receipt

### 4. Operating Expenses
- **Total Operating Expenses**:
  $$\text{Total OpEx} = \sum \text{amount} = \$2,000,000.00$$
  *(2,000 ledger records across 5 branches and 4 cost categories: Salaries, Rent, Utilities, Marketing).*

---

## 5. Frontend Client Architecture & Integration

### Typed API Client (`frontend/lib/api/client.ts`)
The API client provides a unified interface consuming endpoints configured by `process.env.NEXT_PUBLIC_API_URL` (defaulting to `http://localhost:8000/api`):

```typescript
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export const opspulseApi = {
  getHealth: () => fetchApi<HealthStatus>('/health'),
  getOverview: () => fetchApi<OverviewData>('/overview'),
  getSalesSummary: () => fetchApi<SalesSummary>('/sales'),
  getSalesTransactions: (params) => fetchApi<PaginatedResponse<SalesTransaction>>(...),
  getInventorySummary: () => fetchApi<InventorySummary>('/inventory'),
  getInventoryItems: (params) => fetchApi<PaginatedResponse<InventoryItem>>(...),
  getProcurementSummary: () => fetchApi<ProcurementSummary>('/procurement'),
  getProcurementOrders: (params) => fetchApi<PaginatedResponse<PurchaseOrder>>(...),
  getSuppliers: () => fetchApi<SuppliersData>('/suppliers'),
  getExpenses: () => fetchApi<ExpensesData>('/expenses'),
  getMonitoring: () => fetchApi<MonitoringData>('/monitoring'),
  getDataQuality: () => fetchApi<DataQualityData>('/data-quality'),
};
```

### Component UX Enhancements
- **Tabular Pagination**: `SalesTransactionsTable`, `InventoryTable`, and `PurchaseOrdersTable` support asynchronous page navigation (`Page X of Y`), search filtering, and category selection.
- **Diagnostics in Settings**: The Settings page (`/settings`) features a live system connectivity card that verifies the FastAPI backend and PostgreSQL warehouse health in real time.

---

## 6. Verification and Testing Results

### 1. Pytest Backend Test Suite
The complete test suite runs against the live warehouse and mock fixtures:
```text
tests/test_api_endpoints.py ..............                               [ 11%]
tests/test_business_rules.py .......                                     [ 17%]
tests/test_completeness.py ......                                        [ 22%]
tests/test_monitoring_classifier.py .......................              [ 42%]
tests/test_monitoring_collector.py ........                              [ 48%]
tests/test_monitoring_models.py ...............                          [ 61%]
tests/test_monitoring_reporter.py .........                              [ 68%]
tests/test_monitoring_storage.py .....                                   [ 73%]
tests/test_monitoring_volume_extractor.py .........                      [ 80%]
tests/test_referential.py .....                                          [ 84%]
tests/test_reporter.py .                                                 [ 85%]
tests/test_suite_and_runner.py .....                                     [ 89%]
tests/test_uniqueness.py ......                                          [ 94%]
tests/test_validity.py ......                                            [100%]

======================= 119 passed, 1 warning in 37.59s =======================
```
- **36 Data Quality tests** (Day 7)
- **69 Pipeline Observability tests** (Day 8)
- **14 API Integration tests** (Day 10)
- **Total: 119 tests passed (100% pass rate)**

### 2. Frontend Static Analysis & Production Build
```text
> opspulse-frontend@0.1.0 type-check
> tsc --noEmit
(0 errors)

> opspulse-frontend@0.1.0 lint
> next lint
✔ No ESLint warnings or errors

> opspulse-frontend@0.1.0 build
> next build
Route (app)                              Size     First Load JS
┌ ○ /                                    3.85 kB         114 kB
├ ○ /_not-found                          871 B           87.9 kB
├ ○ /data-quality                        3.8 kB          114 kB
├ ○ /expenses                            3.73 kB         114 kB
├ ○ /inventory                           3.54 kB         113 kB
├ ○ /monitoring                          3.85 kB         114 kB
├ ○ /procurement                         3.52 kB         113 kB
├ ○ /sales                               3.54 kB         113 kB
├ ○ /settings                            3.78 kB         114 kB
└ ○ /suppliers                           3.24 kB         113 kB
+ First Load JS shared by all            87 kB
✓ Compiled successfully
```

---

## 7. Local Execution & Startup Guide

### Prerequisites
- Python 3.11+ virtual environment (`.venv`) with dependencies installed (`backend/requirements.txt`).
- Node.js 18+ and npm installed.
- PostgreSQL running locally with `opspulse_dw` populated.

### Step 1: Start the FastAPI Backend Server
In a terminal at the project root:
```powershell
# Set database URL environment variable (if not set globally)
$env:OPSPULSE_DATABASE_URL="postgresql+psycopg://retailflow_admin:111111@127.0.0.1:5432/opspulse_dw"

# Start Uvicorn server with auto-reload
.venv\Scripts\uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation is accessible at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/api/health`

### Step 2: Start the Next.js Frontend
In a second terminal:
```powershell
cd frontend
npm run dev
```
Open `http://localhost:3000` in your web browser. All 9 pages will display live, interactive warehouse data.
