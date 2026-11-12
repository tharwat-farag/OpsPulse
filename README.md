# OpsPulse

### Business Operations & Profitability Intelligence Platform

**See the Signals. Improve the Business.**

---

## Overview

OpsPulse is a Data Engineering portfolio project that demonstrates how retail and distribution businesses can transform fragmented operational data into a centralized analytical platform.

The project integrates sales, inventory, procurement, supplier, branch, customer, and operating expense data into a structured data warehouse.

It applies a Medallion Architecture, dimensional modeling, and SQL analytics to provide business-focused insights into operational performance and profitability.

**Industry:** Retail & Distribution  
**Business Scenario:** Nexa Distribution Group (Fictional)  
**Data:** Synthetic Demonstration Data  
**Current Status:** Data Engineering Foundation Completed – Application Development Planned

---

## Business Challenges

OpsPulse simulates common challenges faced by retail and distribution businesses:

- Limited visibility into branch-level profitability.
- Stockouts and inventory imbalances.
- Difficulty monitoring product profitability.
- Supplier delivery delays.
- Procurement cost variations.
- Fragmented operational data.
- Time-consuming manual reporting.
- Inconsistent data quality.

## Target Business Modules

| Module | Business Purpose | Implementation Status |
|---|---|---|
| Executive Overview | Consolidated business performance and profitability | Planned |
| Sales Intelligence | Revenue, gross profit, sales trends, and product performance | SQL Analytics Implemented |
| Inventory Intelligence | Inventory position, availability, and stockout analysis | SQL Analytics Implemented |
| Procurement Intelligence | Purchase orders, supplier delivery, and purchasing costs | SQL Analytics Implemented |
| Data Pipeline Health | Processing batches and data quality monitoring | Partially Implemented |

---

## Data Engineering Architecture

OpsPulse follows the Medallion Architecture, separating data processing into three logical layers.

### Bronze Layer
- Ingests generated source datasets.
- Preserves raw records.
- Organizes ingestion batches.
- Maintains ingestion manifests.

### Silver Layer
- Cleans and standardizes datasets.
- Applies data validation rules.
- Handles invalid records through quarantine processing.
- Produces structured datasets for analytical processing.

### Gold Layer
- Implements a dimensional data warehouse in PostgreSQL.
- Uses fact, dimension, and bridge tables.
- Supports analytical SQL queries and business KPIs.

### Current Data Flow

```text
Synthetic Data Generation
          |
          v
    Raw CSV Datasets
          |
          v
   Python Ingestion
          |
          v
     Bronze Layer
          |
          v
 Pandas Transformation
          |
          v
     Silver Layer
          |
          v
 PostgreSQL Gold Warehouse
          |
          v
     SQL Analytics
          |
          v
    Business Insights
```

### Planned Application Flow

```text
PostgreSQL Gold Warehouse
          |
          v
      FastAPI Backend
          |
          v
   Next.js Web Dashboard
          |
          v
    Business Users
```

The application flow is part of the development roadmap and is not yet implemented.

---

## Implemented Work

### 1. Synthetic Data Generation

Generated 12 interconnected datasets representing retail and distribution operations.

| Dataset | Records |
|---|---:|
| Sales | 20,000 |
| Inventory Snapshots | 9,000 |
| Customers | 1,000 |
| Purchase Orders | 1,000 |
| Goods Receipts | 1,453 |
| Operating Expenses | 2,000 |
| Products | 100 |
| Branches | 5 |
| Warehouses | 3 |
| Suppliers | 10 |
| Product-Supplier Relationships | 150 |
| Purchase Order Lines | 3,000 |
| **Total** | **37,721** |

All records are synthetically generated for demonstration purposes.

### 2. Data Ingestion and Transformation

Implemented:

- Python-based raw CSV ingestion.
- Batch-based Bronze ingestion.
- Silver transformations using Pandas.
- Dataset validation.
- Invalid record quarantine handling.
- Silver-layer audit checks.
- Processing manifests.

### 3. Dimensional Data Warehouse

Implemented a PostgreSQL analytical warehouse containing 15 tables.

**Dimension Tables (8)**

- `dim_date`
- `dim_product`
- `dim_customer`
- `dim_branch`
- `dim_supplier`
- `dim_warehouse`
- `dim_sales_channel`
- `dim_expense_category`

**Fact Tables (5)**

- `fact_sales`
- `fact_inventory_snapshot`
- `fact_purchase_order_lines`
- `fact_goods_receipts`
- `fact_operating_expenses`

**Bridge Tables (2)**

- `bridge_product_supplier`
- `bridge_branch_warehouse`

The warehouse supports analytical relationships across sales, inventory, procurement, supplier, and operating expense domains.

### 4. SQL Analytics

Created 25 SQL analytical queries covering:

- Sales performance and revenue trends.
- Branch and product profitability.
- Sales channel performance.
- Inventory health and stockout analysis.
- Supplier delivery performance.
- Purchase order fulfillment.
- Purchase cost variance.
- Operating expense analysis.
- Branch-level operating results.
- Profitability reconciliation.

### 5. Data Validation and Warehouse Auditing

Implemented validation and audit checks covering:

- Dataset processing results.
- Silver-layer audit.
- Warehouse referential integrity.
- Fact table grain and duplicate checks.
- Orphan record checks.
- Profitability reconciliation.

---

## Selected Business Metrics

The current synthetic dataset produces the following analytical results:

| Metric | Result |
|---|---:|
| Sales Lines | 20,000 |
| Invoices | 8,053 |
| Net Revenue | EGP 357.43M |
| Gross Profit | EGP 45.43M |
| Gross Profit Margin | 12.71% |
| Operating Expenses | EGP 39.63M |
| Simplified Operating Result | EGP 5.80M |

**Important metric definitions:**

- Net Revenue is calculated after discounts.
- Gross Profit is Net Revenue minus sales cost.
- Simplified Operating Result is Gross Profit minus operating expenses.
- Simplified Operating Result is not a complete accounting net profit.
- These figures are generated from synthetic data and do not represent real business performance.

---

## Technology Stack

### Implemented

- Python
- Pandas
- NumPy
- Faker
- PostgreSQL
- SQLAlchemy
- Psycopg
- SQL
- Docker
- Git

### Planned

- Microsoft Fabric
- OneLake
- PySpark
- Fabric Data Factory
- FastAPI
- Next.js
- TypeScript
- Tailwind CSS
- Recharts
- Enhanced Pipeline Orchestration

---

## Project Structure

```text
OpsPulse/
|
|-- docs/
|   |-- architecture.md
|   |-- business-requirements.md
|
|-- data/
|   |-- raw/
|   |-- bronze/
|   |-- silver/
|   |-- gold/
|
|-- backend/
|   |-- requirements.txt
|   |-- src/
|       |-- analytics/
|       |-- data_generation/
|       |-- ingestion/
|       |-- profiling/
|       |-- transformation/
|       |-- validation/
|       |-- warehouse/
|           |-- loaders/
|           |-- sql/
|
|-- frontend/
|-- infrastructure/
|-- tests/
|
|-- .gitignore
|-- README.md
```

Generated datasets, local environment files, and virtual environments are excluded from version control.

---

## Development Roadmap

| Day | Milestone | Status |
|---|---|---|
| 1 | Project Foundation & Architecture | Completed |
| 2 | Synthetic Data Generation & Ingestion | Completed |
| 3 | Bronze and Silver Processing | Completed |
| 4 | PostgreSQL Dimensional Data Warehouse | Completed |
| 5 | SQL Analytics & Business KPIs | Completed |
| 6 | Microsoft Fabric & OneLake Integration | Planned |
| 7 | Data Quality & Pipeline Orchestration | Planned |
| 8 | FastAPI Backend | Planned |
| 9 | Interactive Next.js Dashboard | Planned |
| 10 | Integration, Testing & Deployment | Planned |

---

## Local Setup

### Prerequisites

- Python 3.13
- Docker Desktop
- PostgreSQL 16 (or the project's configured PostgreSQL container)
- Git

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd OpsPulse
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install -r .\backend\requirements.txt
```

### 4. Configure Database Connection

Set the `OPSPULSE_DATABASE_URL` environment variable with your own PostgreSQL connection string.

Example format:

```text
postgresql+psycopg://<username>:<password>@<host>:<port>/<database>
```

**PowerShell:**

```powershell
$env:OPSPULSE_DATABASE_URL = "YOUR_DATABASE_CONNECTION_STRING"
```

Never commit `.env` files, database passwords, or secret credentials.

### 5. Verify Database Connectivity

```powershell
python .\backend\src\warehouse\test_connection.py
```

The database must be running and the required warehouse schemas and tables must already exist.

---

## Important Project Notes

- All demonstration data is synthetic.
- The branch-to-warehouse mapping is an explicitly documented project assumption.
- Current SCD Type 2 dimensions contain baseline versions; historical change processing remains to be implemented and tested.
- Historical inventory snapshot values must not be summed and interpreted as current inventory value.
- Stockout indicators do not automatically represent confirmed lost sales.
- Supplier on-time delivery is measured at the goods-receipt event level.
- Purchase order fulfillment is measured at the purchase-order-line level.
- Purchase cost variance currently uses reference supplier prices, not verified historical contract prices.
- Branch profitability represents a simplified operating result, not complete net profit.
- Microsoft Fabric and OneLake integration are planned, not yet implemented.
- FastAPI and the Next.js dashboard are planned application components.

---

## Project Goals

OpsPulse demonstrates practical Data Engineering capabilities through:

- Synthetic data generation.
- Batch data ingestion.
- Medallion Architecture.
- Data cleaning and validation.
- Dimensional data modeling.
- PostgreSQL Data Warehousing.
- SQL Analytics.
- Business KPI development.
- Data quality and reconciliation.

---

**OpsPulse — Turning Operational Data into Better Business Decisions.**