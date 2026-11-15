# OpsPulse — Retail & Distribution Operations Intelligence Platform

> **See the Signals. Optimize Operations. Accelerate Profitability.**

OpsPulse is an enterprise-grade Data Engineering and Business Intelligence platform built for retail and distribution networks. It unifies fragmented transactional streams across sales, inventory, procurement, suppliers, and operating expenses into a centralized PostgreSQL Data Warehouse (`opspulse_dw`), governed by automated data quality assertions, full pipeline observability, a high-performance Python FastAPI analytical backend, and a modern Next.js 14 App Router executive dashboard.

---

## 1. Project Overview & Business Problem

### Business Context & Objectives
Retail and wholesale distribution companies frequently struggle with operational silos, fragmented transactional systems, delayed reporting cadences, and silent data quality degradation. In multi-branch, multi-warehouse distribution businesses (such as the simulated *Nexa Distribution Group*):
- **Margin Erosion:** Product discounting and localized logistics costs erode profitability without real-time visibility.
- **Supply Chain Bottlenecks:** Purchase orders experience unmonitored vendor lead-time slippage and partial dock fulfillment issues.
- **Stockout & Capital Imbalances:** Warehouses experience high stockout rates on critical SKUs while holding excess dead stock in non-moving lines.
- **Data Quality Blind Spots:** Dirty, duplicate, or orphan records silently propagate into executive dashboards, destroying analytical credibility.

OpsPulse addresses these challenges by implementing an end-to-end data platform with automated ingestion, quarantined cleaning, star-schema dimensional modeling, automated data quality scoring, end-to-end pipeline lineage observability, and sub-second analytical querying.

---

## 2. Key Platform Features

- **Medallion Data Architecture:** Robust Bronze (raw staging), Silver (validated & quarantined transformations), and Gold (dimensional warehouse) layers.
- **Enterprise Star Schema:** Dimensional modeling featuring 6 dimensions, 2 bridge tables, and 5 granular fact tables handling 20,000+ sales lines, 9,000 inventory snapshots, and 1,000 purchase orders.
- **Automated Data Quality Framework:** 210 programmatic assertions executing across Completeness, Uniqueness, Validity, Referential Integrity, and Business Logic with automated quarantine routing.
- **Full Pipeline Observability:** Medallion volume lineage tracking, task execution duration telemetry, and root-cause failure classification persisted in dedicated PostgreSQL `monitoring` schemas.
- **Orchestration with Apache Airflow 3.4.0:** 30-task directed acyclic graph (DAG) automating data extraction, transformation, quality gates, dimensional loading, and telemetry reporting.
- **FastAPI Analytical Backend:** 12 parameterized REST endpoints with connection pooling, structured error handling, and sub-50ms query response times.
- **Executive Next.js 14 Dashboard:** 9 purpose-built operational interfaces with Recharts data visualizations, global DateRange filtering (FY 2025, Q1–Q4), responsive mobile/tablet layout, and persistent user configuration.

---

## 3. Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Data Sources [Data Sources & Generation]
        RAW[Synthetic Retail Data Generator<br/>Sales, Inventory, POs, Expenses] -->|Raw CSVs| BRONZE[Bronze Layer Staging<br/>Raw Batches & Ingestion Manifests]
    end

    subgraph Orchestration [Apache Airflow 3.4.0 DAG]
        BRONZE -->|Audit & Validate| SILVER[Silver Transformation Engine<br/>Pandas Standardization & Cleaning]
        SILVER -->|Invalid Records| QUARANTINE[(Quarantine Datasets)]
        SILVER -->|Valid Records| DQ_GATE[Data Quality Engine<br/>210 Automated Assertions]
        DQ_GATE -->|Pass 100%| GOLD_LOAD[Gold Dimension & Fact Loaders]
        
        subgraph Observability [Observability & Telemetry]
            AIRFLOW_METRICS[Pipeline Run Metrics]
            TASK_METRICS[Task Duration Telemetry]
            VOL_LINEAGE[Medallion Volume Extractor]
        end
    end

    subgraph Warehouse [PostgreSQL 16 Data Warehouse opspulse_dw]
        GOLD_LOAD --> GOLD_SCHEMA[(Gold Dimensional Schema<br/>6 Dims, 2 Bridges, 5 Facts)]
        AIRFLOW_METRICS --> MON_SCHEMA[(Monitoring Schema<br/>Lineage & Failure Telemetry)]
        TASK_METRICS --> MON_SCHEMA
        VOL_LINEAGE --> MON_SCHEMA
    end

    subgraph Serving [Analytical Serving & Application Layer]
        GOLD_SCHEMA --> FASTAPI[FastAPI REST API<br/>Port 8000 / Uvicorn]
        MON_SCHEMA --> FASTAPI
        FASTAPI -->|JSON REST API| NEXTJS[Next.js 14 Enterprise Dashboard<br/>App Router / Port 3000]
        NEXTJS -->|Browser Client| USER((Executive / Ops Manager))
    end
```

---

## 4. Medallion Data Engineering Workflow

OpsPulse structures its data processing into three distinct stages:

### Bronze Layer (Raw Staging)
- Ingests raw source CSV extracts preserving complete transactional lineage.
- Generates batch UUIDs and metadata manifests recording file hashes, timestamps, and row counts.
- Stores immutable point-in-time snapshots to ensure full pipeline replayability.

### Silver Layer (Transformation & Quarantine)
- Enforces strict data types, standardizes naming conventions, and parses ISO timestamps.
- Evaluates domain-specific business rules (e.g., non-negative quantities, valid price bounds).
- Implements **Quarantine Routing**: Records failing schema or validity checks are routed to `_quarantine.csv` sinks with exact error reason codes, ensuring clean downstream tables without stopping pipeline execution.

### Gold Layer (Dimensional Warehouse)
- Implements Kimball star-schema dimensional modeling inside PostgreSQL (`opspulse_dw`).
- Generates surrogate integer keys, enforces foreign key referential integrity, and maintains Slowly Changing Dimension (SCD Type 1) semantics.

---

## 5. PostgreSQL Warehouse Schema & Dimensional Model

The Gold schema is optimized for analytical rollups, aggregations, and high-performance slicing:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DIMENSION & BRIDGE TABLES                       │
├─────────────────────────┬────────────────────────┬─────────────────────┤
│ gold.dim_product        │ 100 SKUs across 6 categories                 │
│ gold.dim_customer       │ 1,000 Retail & Wholesale Accounts            │
│ gold.dim_branch         │ 5 Regional Hubs (Cairo, Giza, Alex, etc.)    │
│ gold.dim_warehouse      │ 3 Distribution Facilities                    │
│ gold.dim_supplier       │ 10 Active Registered Suppliers               │
│ gold.dim_date           │ Calendar Dimension (20250101 – 20251231)     │
│ gold.dim_expense_cat    │ 5 Operational Cost Categories                │
│ bridge_product_supplier │ 150 SKU-Supplier Mapping Lines               │
│ bridge_branch_warehouse │ 15 Logistics Route Allocations               │
└─────────────────────────┴────────────────────────┴─────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              FACT TABLES                               │
├─────────────────────────┬──────────────────────────────────────────────┤
│ gold.fact_sales         │ 20,000 transaction lines (8,053 invoices)   │
│ fact_inventory_snapshot │ 9,000 warehouse snapshot rows (300 SKU-sites)│
│ fact_purchase_order_lns │ 3,000 purchase order lines (1,000 POs)       │
│ gold.fact_goods_receipt │ 1,453 dock delivery inspection events        │
│ fact_operating_expenses │ 2,000 monthly operational expense lines      │
└─────────────────────────┴──────────────────────────────────────────────┘
```

---

## 6. Pipeline Orchestration with Apache Airflow 3.4.0

The entire pipeline is automated through the `opspulse_pipeline` DAG in Apache Airflow 3.4.0:

1. **Bronze Ingestion Phase:** Parallel ingestion of 12 transactional streams with batch manifest tracking.
2. **Silver Transformation Phase:** Standardized cleansing, casting, and quarantine routing across all datasets.
3. **Data Quality Verification Gate:** Automated execution of the 210-assertion test suite. Pipeline fails fast if critical integrity constraints are breached.
4. **Gold Warehouse Loading Phase:** Dimension population, bridge table synchronization, and fact table surrogate key lookups.
5. **Observability Telemetry Phase:** Automated extraction of run duration, step success rates, and Medallion volume progression into the `monitoring` schema.

---

## 7. Automated Data Quality Framework

OpsPulse features an enterprise data quality engine (`backend/src/validation/data_quality/`):
- **210 Automated Assertions** executed on every pipeline run across 12 Silver datasets.
- **100% Pass Rate** verified in production:
  - **Completeness (48 checks):** Mandatory non-null constraints on primary keys, transaction dates, and financial amounts.
  - **Uniqueness (32 checks):** Primary key and composite natural key uniqueness verification.
  - **Validity (44 checks):** Numerical domain bounds (e.g., `unit_price > 0`, `discount_rate BETWEEN 0 AND 0.50`), regex email validation, and foreign key accepted values.
  - **Referential Integrity (24 checks):** Parent-child relational checks preventing orphan transactions.
  - **Business Rules (62 checks):** Complex cross-column validations (e.g., `accepted_qty <= received_qty`, `gross_amount == quantity * unit_price`).
- **Reporting:** Generates machine-readable `latest_quality_report.json` and audit CSVs exposed via `/api/data-quality`.

---

## 8. Pipeline Observability & Telemetry

Pipeline operations are fully observable via dedicated tables in the `monitoring` schema:
- `monitoring.pipeline_run_metrics`: Wall-clock execution duration, start/end timestamps, and overall DAG health.
- `monitoring.pipeline_task_metrics`: Granular task-level status, execution duration (seconds), and error tracebacks.
- `monitoring.pipeline_data_volume_metrics`: End-to-end Medallion volume tracking:
  $$\text{Raw Records: } 150,627 \longrightarrow \text{Bronze: } 150,627 \longrightarrow \text{Silver: } 150,627 \longrightarrow \text{Gold: } 150,627$$
- Visualized natively in the frontend via interactive Sankey/Medallion volume lineage and task duration charts.

---

## 9. FastAPI Analytical Backend

Located in `backend/src/api/`, the backend serves sub-50ms analytics to the frontend:
- **Architecture:** FastAPI on Uvicorn with SQLAlchemy 2.0 connection pooling (`psycopg` 3.x driver).
- **Security & Reliability:** Parameterized SQL queries preventing injection, strict CORS whitelisting, and centralized JSON exception handlers.
- **12 Domain Endpoints:**
  - `GET /api/health` — PostgreSQL connection ping and service status.
  - `GET /api/overview` — Executive KPIs, monthly revenue curve, top SKUs, branch performance (supports `?quarter=1..4`).
  - `GET /api/sales` — Revenue breakdown, discount metrics, margin analysis.
  - `GET /api/sales/transactions` — Server-side paginated transaction ledger (search, channel, quarter filters).
  - `GET /api/inventory` — Facility capacity utilization and valuation metrics.
  - `GET /api/inventory/items` — Paginated SKU ledger with stockout flags and warehouse filtering.
  - `GET /api/procurement` — Committed PO spend, supplier lead times, OTIF delivery rate.
  - `GET /api/procurement/orders` — Paginated purchase order registry with supplier filtering.
  - `GET /api/suppliers` — Supplier scorecard directory with fulfillment rates and risk ratings.
  - `GET /api/expenses` — OpEx ledger, monthly budget variance, cost center distribution.
  - `GET /api/monitoring` — Real-time Airflow DAG execution history and task-level duration telemetry.
  - `GET /api/data-quality` — 210 assertion test results, dataset health scores, and categorical breakdowns.

---

## 10. Next.js 14 Enterprise Dashboard

The modern web application in `frontend/` provides 9 intuitive, data-dense screens:
- **Next.js 14 App Router:** TypeScript, Tailwind CSS, Lucide icons, and Recharts SVG graphics.
- **Global DateRange Context:** Top navigation selector (`FY 2025`, `Q1 2025`, `Q2 2025`, `Q3 2025`, `Q4 2025`, `All Available Data`) with `localStorage` persistence dynamically updates charts across Overview, Sales, and Expenses.
- **Enterprise UX:** Compact currency formatting (`$357.43M`, `$29.5M`), KPI sentiment indicators, instant search, table pagination, and responsive design across desktop, laptop, and tablet viewports.
- **Persistent Settings:** Configurable auto-refresh polling intervals (`Off`, `30s`, `1m`, `5m`) persisted in browser storage.

---

## 11. Authoritative Business Metrics Reconciled

All metrics displayed across the platform reconcile 100% with the PostgreSQL warehouse:

| Metric Name | Reconciled Value | Source Formula & Definition |
| :--- | :--- | :--- |
| **Gross Sales Amount** | **$380,108,747.31** | $\sum (\text{quantity} \times \text{unit\_price})$ across 20,000 sales lines |
| **Total Discounts** | **$22,681,878.26** | Total promotional price reductions deducted from sales |
| **Net Sales Revenue** | **$357,426,869.05** | $\text{Gross Sales} - \text{Discounts}$ across 8,053 customer invoices |
| **Gross Profit** | **$45,431,649.88** | $\text{Net Revenue} - \text{COGS}$ (Gross Margin: **12.71%**) |
| **Distinct Invoices** | **8,053 Invoices** | Average Order Value (AOV): **$44,384.31** |
| **Current Inventory Valuation** | **$17,169,853.11** | Latest snapshot valuation across 300 SKU-warehouse sites |
| **Stockout Rate (Latest)** | **18.0%** | 54 out of 300 SKU locations currently out of stock |
| **Committed PO Spend** | **$360,560,754.34** | Contractually committed spend across 782 Open POs (1,000 total POs) |
| **Goods Receipt Acceptance Rate** | **95.7% (Avg)** | **95.7%** per-receipt average; **97.7%** aggregate accepted units (48,048 / 49,184) |
| **Supplier OTIF Delivery Rate** | **94.2%** | Dock receipts delivered on-time meeting specifications |
| **Average Supplier Lead Time** | **8.4 Business Days** | Time elapsed between PO order placement and dock warehouse delivery |
| **Total Operating Expenses (OpEx)** | **$39,631,974.00** | Full year 2025 operating expenditures (11.1% OpEx-to-Net Revenue ratio) |

---

## 12. Tech Stack

- **Data Engineering:** Python 3.13, Pandas, NumPy, SQLAlchemy 2.0, Psycopg 3.
- **Database & Warehouse:** PostgreSQL 16 (Star Schema, SCD Type 1, Medallion Architecture).
- **Orchestration:** Apache Airflow 3.4.0 (Custom DAGs, Batch Tracking).
- **Backend API:** FastAPI, Uvicorn, Pydantic v2, AnyIO.
- **Frontend UI:** Next.js 14.2 (App Router), React 18, TypeScript, Tailwind CSS, Recharts, Lucide React.
- **Quality & Testing:** Pytest, Faker, Chrome DevTools Protocol (CDP) automated browser testing.

---

## 13. Repository Structure

```text
OpsPulse/
├── airflow/
│   └── dags/
│       └── opspulse_pipeline.py          # 30-task Airflow 3.4.0 pipeline DAG
├── backend/
│   ├── requirements.txt                  # Python production dependencies
│   └── src/
│       ├── api/                          # FastAPI application & route handlers
│       │   ├── database.py               # SQLAlchemy connection pool
│       │   ├── main.py                   # FastAPI app entry point & CORS
│       │   └── routes/                   # 10 modular analytical domain routes
│       ├── data_generation/              # Synthetic business data generator
│       ├── ingestion/                    # Bronze layer extraction & manifests
│       ├── monitoring/                   # Observability engine & collectors
│       ├── transformation/               # Silver layer cleansing & quarantine
│       ├── validation/data_quality/      # 210-assertion Data Quality engine
│       └── warehouse/loaders/            # Gold dimensional loaders
├── data/
│   ├── bronze/                           # Staging folder (.gitkeep)
│   ├── silver/                           # Cleansed folder (.gitkeep)
│   ├── gold/                             # Warehouse export folder (.gitkeep)
│   ├── monitoring_reports/               # Telemetry JSON/CSV summaries
│   └── quality_reports/                  # Latest DQ report JSON/CSV
├── docs/                                 # Architectural runbooks & dictionaries
│   ├── business_metrics_dictionary.md    # Definitive KPI calculation formulas
│   ├── final_project_stabilization_report.md # Full audit & reconciliation report
│   └── operational_runbook.md            # Maintenance & disaster recovery guide
├── frontend/                             # Next.js 14 App Router web dashboard
│   ├── app/                              # 9 Application routes
│   ├── components/                       # Reusable UI, Charts, and Tables
│   ├── lib/                              # API client, DateRange context, utils
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── tests/                                # 121 unit and integration tests
├── .env.example                          # Sanitized environment configuration
├── .gitignore                            # Production git exclusions
├── pytest.ini                            # Pytest test suite configuration
├── README.md                             # Comprehensive project documentation
└── start_opspulse.ps1                    # Unified local startup script
```

---

## 14. Local Installation & Quickstart

### Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Node.js 18.x or 20.x
- PostgreSQL 15+ running locally on port 5432

### 1. Clone & Setup Environment
```bash
git clone https://github.com/tharwat-farag/OpsPulse.git
cd OpsPulse

# Create and activate Python virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables
```bash
# Copy template to .env
cp .env.example .env

# Configure your local PostgreSQL connection in .env:
# OPSPULSE_DATABASE_URL=postgresql+psycopg://username:password@127.0.0.1:5432/opspulse_dw
```

### 3. Initialize Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 4. Run the Platform
You can start both the FastAPI backend and Next.js frontend using the provided launcher:
```powershell
# Windows PowerShell
.\start_opspulse.ps1
```
Or start each service independently:
```bash
# Terminal 1 - Backend (Port 8000)
$env:PYTHONPATH="backend/src"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Frontend (Port 3000)
cd frontend
npm run dev
```

Visit `http://localhost:3000` to view the live dashboard.

---

## 15. Testing & Verification

### Running Backend & Data Quality Tests
OpsPulse includes 121 automated tests covering API endpoints, data quality assertions, schema classifiers, and storage layers:
```bash
.venv\Scripts\pytest -v
# Output: ======================= 121 passed, 1 warning in 15.78s =======================
```

### Running Frontend Validation
```bash
cd frontend
# TypeScript type check
npm run type-check   # 0 errors

# ESLint code hygiene
npm run lint         # 0 warnings or errors

# Production build verification
npm run build        # Compiled successfully (12/12 static pages)
```

---

## 16. Deployment Architecture

The production-ready deployment architecture decouples compute from storage:
- **Frontend Dashboard:** Deployed on **Vercel** via Next.js Edge / Serverless hosting with optimized static caching and reverse-proxy API routing.
- **API Backend:** Containerized Python FastAPI application hosted on cloud infrastructure (e.g. Render, Railway, or Google Cloud Run) communicating over secure HTTPS.
- **Database:** Managed Cloud PostgreSQL instance hosting the `gold` dimensional warehouse and `monitoring` schemas.
- **Security:** All database credentials and API secrets remain strictly server-side. Zero sensitive keys or internal connection strings are exposed in client-side bundles.

---

## 17. Synthetic Data Disclaimer & Limitations

- **Synthetic Data:** All transactional records, invoices, customer names, vendor scorecards, and addresses were synthetically generated using Python's `Faker` library for the fictional company *Nexa Distribution Group*. No real commercial or customer PII is contained in this repository.
- **Calendar Scope:** Transactional data is bounded within calendar year 2025 (`2025-01-01` to `2025-12-31`). Selecting date intervals outside this window returns empty sets.
- **Airflow Orchestration:** In local development, Airflow DAGs execute against the local PostgreSQL warehouse. In cloud demo mode, the dashboard and API read the pre-aggregated Gold warehouse and persisted monitoring telemetry to maintain low operational cost without requiring a persistent 24/7 Airflow server.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
