# OpsPulse — Retail & Distribution Operations Intelligence Platform

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.13](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL: 16](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Airflow: 3.4.0](https://img.shields.io/badge/Apache_Airflow-3.4.0-017CEE.svg?logo=apache-airflow&logoColor=white)](https://airflow.apache.org/)
[![FastAPI: 0.115](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js: 14](https://img.shields.io/badge/Next.js-14_App_Router-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript: 5](https://img.shields.io/badge/TypeScript-5-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tests: 129 Passed](https://img.shields.io/badge/Tests-129_Passed-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![Data Quality: 100%](https://img.shields.io/badge/Data_Quality-100%25_(210_Checks)-emerald.svg)](backend/src/validation/data_quality/)

**An enterprise-grade, end-to-end Data Engineering & Operations Intelligence Platform unifying fragmented multi-branch retail distribution streams into a medallion-governed PostgreSQL warehouse, powered by Apache Airflow, FastAPI, and Next.js 14.**

[Live Production Dashboard](https://opspulse-frontend-seven.vercel.app) • [Live Analytical API](https://ops-pulse-lake.vercel.app) • [Interactive API Docs (Swagger)](https://ops-pulse-lake.vercel.app/docs) • [API Health Status](https://ops-pulse-lake.vercel.app/api/health)

</div>

---

## Table of Contents
1. [Live Production Deployments](#1-live-production-deployments)
2. [Project Overview](#2-project-overview)
3. [Business Problem & Objectives](#3-business-problem--objectives)
4. [Key Engineering Highlights](#4-key-engineering-highlights)
5. [End-to-End System Architecture](#5-end-to-end-system-architecture)
6. [Medallion Data Engineering Pipeline](#6-medallion-data-engineering-pipeline)
7. [Technology Stack](#7-technology-stack)
8. [Data Sources & Dataset Overview](#8-data-sources--dataset-overview)
9. [Data Warehouse Design & Dimensional Modeling](#9-data-warehouse-design--dimensional-modeling)
10. [Apache Airflow Orchestration](#10-apache-airflow-orchestration)
11. [Automated Data Quality Framework](#11-automated-data-quality-framework)
12. [Pipeline Observability & Lineage Telemetry](#12-pipeline-observability--lineage-telemetry)
13. [Backend API Architecture (FastAPI)](#13-backend-api-architecture-fastapi)
14. [Frontend Executive Dashboard (Next.js 14)](#14-frontend-executive-dashboard-nextjs-14)
15. [Cloud Deployment Architecture (Vercel + Neon)](#15-cloud-deployment-architecture-vercel--neon)
16. [Authoritative Business KPIs & Reconciliation](#16-authoritative-business-kpis--reconciliation)
17. [Testing, Quality Assurance & Verification](#17-testing-quality-assurance--verification)
18. [Local Installation & Quickstart](#18-local-installation--quickstart)
19. [Repository Structure](#19-repository-structure)
20. [Documentation Index & Deep Dives](#20-documentation-index--deep-dives)
21. [License & Disclaimer](#21-license--disclaimer)

---

## 1. Live Production Deployments

The entire OpsPulse platform is deployed and running in a serverless, decoupled cloud architecture:

| Component | Service | Live Production URL | Description |
| :--- | :--- | :--- | :--- |
| **Frontend Dashboard** | Vercel (Edge/Serverless) | [https://opspulse-frontend-seven.vercel.app](https://opspulse-frontend-seven.vercel.app) | Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts |
| **Backend API** | Vercel (Python Serverless) | [https://ops-pulse-lake.vercel.app](https://ops-pulse-lake.vercel.app) | FastAPI ASGI analytical engine serving 12 domain endpoints |
| **API Documentation** | Swagger UI | [https://ops-pulse-lake.vercel.app/docs](https://ops-pulse-lake.vercel.app/docs) | Interactive OpenAPI 3.0 specification & live endpoint test bench |
| **Backend Health** | Monitoring Probe | [https://ops-pulse-lake.vercel.app/api/health](https://ops-pulse-lake.vercel.app/api/health) | Live PostgreSQL warehouse connectivity probe |
| **Cloud Warehouse** | Neon PostgreSQL | Cloud Data Warehouse (`neondb`) | Managed serverless PostgreSQL hosting `gold` & `monitoring` schemas |

---

## 2. Project Overview

**OpsPulse** is a production-grade data engineering showcase modeled after real-world multi-facility distribution operations (*Nexa Distribution Group*). It ingests, validates, cleanses, models, and serves high-volume transactional streams spanning **Sales & Invoicing, Warehouse Inventory Snapshots, Purchase Orders, Dock Goods Receipts, and Operating Expenses (OpEx)**.

Rather than relying on disjointed notebooks or mock JSON feeds, OpsPulse demonstrates a complete, enterprise-caliber data lifecycle:
- **Raw Transaction Ingestion** with cryptographic batch manifests and point-in-time snapshotting.
- **Silver Cleansing & Quarantine Routing** discarding dirty data without halting pipeline execution.
- **Enterprise Star Schema Modeling** enforcing Kimball dimensional modeling principles inside PostgreSQL.
- **Automated Data Quality Gates** verifying 210 programmatic constraints with a 100% pass rate.
- **Production Airflow Orchestration** running 30 automated tasks with execution duration telemetry.
- **Sub-50ms REST API Serving** using FastAPI with parameterized SQL and serverless-safe connection pooling.
- **Data-Dense Executive Frontend** delivering interactive analytical visualisations with sub-second page loads.

---

## 3. Business Problem & Objectives

Wholesale and retail distribution networks frequently encounter severe operational inefficiencies caused by disparate transactional systems:

1. **Silent Profit Margin Erosion:** Heavy promotional discounting across decentralized retail channels obscures true gross margin performance.
2. **Stockout vs. Overstock Imbalances:** Inaccurate demand visibility leads to concurrent 18% stockout rates on high-velocity items alongside bloated capital trapped in dead inventory.
3. **Vendor Delivery & Fulfillment Volatility:** Inconsistent vendor lead times and partial dock receipts delay fulfillment across regional distribution hubs.
4. **Data Fragmentation & Analytical Distrust:** Untracked changes, orphan records, and corrupt schemas silently corrupt decision-making dashboards.

### Quantifiable Engineering Objectives
- Unify 5 operational domains into a **single source of truth** dimensional warehouse.
- Ensure **zero orphan records** across all fact tables through automated referential integrity gates.
- Implement **100% automated test coverage** across critical data constraints prior to warehouse loading.
- Enable **sub-second analytical query execution** for executive decision-makers across 12 analytical dimensions.

---

## 4. Key Engineering Highlights

- **Robust Medallion Architecture:** Explicit separation of concerns across Bronze (raw staging), Silver (standardized, cleaned, quarantined), and Gold (star-schema dimensional warehouse).
- **Kimball Dimensional Modeling:** 8 dimensions, 2 bridge tables, and 5 granular fact tables modeling 37,000+ business records across a conformed star schema (150,627 cumulative Medallion layer observations).
- **Automated Data Quality Gate (210 Checks):** Automated validation suite executing across Completeness, Uniqueness, Validity, Referential Integrity, and Business Logic with automated quarantine routing.
- **Full Pipeline Observability:** End-to-end Medallion volume lineage tracking, task execution duration telemetry, and root-cause failure classification persisted in dedicated PostgreSQL `monitoring` schemas.
- **Production Airflow 3.4.0 DAG:** 30-task directed acyclic graph automating ingestion, transformation, quality gates, warehouse loading, and observability telemetry in 28.32 seconds.
- **High-Performance FastAPI Backend:** 12 parameterized endpoints utilizing SQLAlchemy 2.0 with automated `NullPool` serverless configuration, preventing connection leaks on Neon PostgreSQL.
- **Decoupled Cloud Architecture:** Deployed completely serverlessly using Vercel (Next.js 14 Frontend + FastAPI Backend) and Neon PostgreSQL, eliminating VM hosting costs entirely.
- **129 Passing Automated Tests:** Full test coverage across backend endpoints, schema validators, data quality suites, and serverless runtime entrypoints.

---

## 5. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Sourcing ["1. Data Sources & Generation"]
        SRC["Synthetic Retail Transaction Engine<br/>• Sales Invoices (20,000 lines)<br/>• Inventory Snapshots (9,000 sites)<br/>• Purchase Orders (3,000 lines)<br/>• Dock Receipts (1,453 events)<br/>• Operating Expenses (2,000 lines)"]
    end

    subgraph Medallion ["2. Medallion Data Engineering Engine"]
        BRONZE["Bronze Layer (Raw Staging)<br/>• Immutable CSV storage<br/>• Batch UUIDs & Ingestion Manifests"]
        SILVER["Silver Layer (Cleansing & Standardization)<br/>• Type Casting & Timestamp Parsing<br/>• Negative Quantity Cleansing"]
        QUARANTINE[("Quarantine Datasets<br/>• Rejected Records<br/>• Reason Error Codes")]
        DQ_GATE{"Data Quality Gate<br/>210 Automated Assertions<br/>(100% Pass Rate)"}
        GOLD["Gold Layer Loaders<br/>• Surrogate Key Lookups<br/>• SCD Type 1 Upserts"]

        SRC -->|Automated Extraction| BRONZE
        BRONZE -->|Audit & Transform| SILVER
        SILVER -->|Validation Failure| QUARANTINE
        SILVER -->|Validation Success| DQ_GATE
        DQ_GATE -->|Pass All 210 Rules| GOLD
    end

    subgraph Orchestration ["3. Orchestration & Observability (Apache Airflow 3.4.0)"]
        DAG["Airflow DAG: opspulse_pipeline<br/>30 Tasks | 28.32s Execution"]
        DAG -.->|Triggers| BRONZE
        DAG -.->|Triggers| SILVER
        DAG -.->|Triggers| DQ_GATE
        DAG -.->|Triggers| GOLD
        TELEMETRY[("Monitoring Schema<br/>• Pipeline Run Telemetry<br/>• Task Durations<br/>• Medallion Volume Lineage")]
        DAG -->|Persists Metrics| TELEMETRY
    end

    subgraph Storage ["4. Cloud Data Warehouse (PostgreSQL / Neon)"]
        GOLD --> DW_GOLD[("gold.* Schemas<br/>• 6 Dimensions<br/>• 2 Bridge Tables<br/>• 5 Fact Tables")]
        TELEMETRY --> DW_MON[("monitoring.* Schemas<br/>• Execution Logs<br/>• Volume Lineage")]
    end

    subgraph Serving ["5. Serving & Presentation Layer"]
        FASTAPI["FastAPI Analytical Backend<br/>(Vercel Serverless Function)<br/>• 12 Parameterized Endpoints<br/>• SQLAlchemy NullPool + psycopg3"]
        NEXTJS["Next.js 14 Executive Dashboard<br/>(Vercel Edge / Serverless)<br/>• 9 Analytical Interfaces<br/>• Recharts Visualizations"]
        CLIENT(("Executive / Ops Analyst"))

        DW_GOLD --> FASTAPI
        DW_MON --> FASTAPI
        FASTAPI -->|JSON REST API| NEXTJS
        NEXTJS -->|Interactive Web UI| CLIENT
    end
```

---

## 6. Medallion Data Engineering Pipeline

```
  ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
  │  BRONZE LAYER  │  ────►  │  SILVER LAYER  │  ────►  │   GOLD LAYER   │
  │  Raw Staging   │         │ Cleaned/Typed  │         │  Star Schema   │
  └────────────────┘         └────────────────┘         └────────────────┘
          │                          │                          │
   Batch Manifests             DQ Quarantine               Dimensional DW
   Raw CSV Archives         210 Quality Assertions      5 Facts & 6 Dimensions
```

### Bronze Layer (Raw Staging)
- **Objective:** Ingest raw, unaltered CSV transaction extracts while preserving complete point-in-time data lineage.
- **Batch Tracking:** Each ingestion batch generates a UUID, recording file checksums, record counts, and timestamps in an immutable JSON manifest.
- **Replayability:** Historical raw batches remain read-only to support complete pipeline reprocessing and disaster recovery.

### Silver Layer (Cleansing & Quarantine)
- **Transformation Engine:** Standardizes column naming, parses ISO-8601 timestamps, validates primary keys, and casts numeric representations using vectorized Pandas routines.
- **Quarantine Sink Routing:** Defective or corrupt records (e.g., negative inventory levels, malformed email strings, out-of-bounds discount rates) are automatically diverted to `_quarantine.csv` sinks with structured error reason codes. Downstream analytics are protected without terminating batch execution.

### Gold Layer (Dimensional Data Warehouse)
- **Kimball Star Schema:** Loads validated records into relational dimension and fact tables in PostgreSQL (`opspulse_dw`).
- **Surrogate Keys:** Replaces natural business identifiers with synthetic integer surrogate keys generated via `GENERATED ALWAYS AS IDENTITY`.
- **SCD Management:** Implements Slowly Changing Dimension (SCD Type 1) semantics to maintain current, high-fidelity dimension state across all downstream analytical queries.

---

## 7. Technology Stack

| Layer | Technologies | Rationale & Purpose |
| :--- | :--- | :--- |
| **Data Engineering** | Python 3.13, Pandas, NumPy, Faker | High-performance vectorised transformation, data validation, and synthetic business stream generation. |
| **Data Warehouse** | PostgreSQL 16 (Local), Neon PostgreSQL (Cloud) | Enterprise relational warehouse implementing star schemas, relational integrity, surrogate identity keys, and B-Tree indexes. |
| **Orchestration** | Apache Airflow 3.4.0 (WSL / Local) | Directed Acyclic Graph (DAG) automating 30 tasks with task-level duration tracking and error alerting. |
| **Data Quality** | Custom Pytest Framework, Python Assertions | 210 programmatic validation assertions verifying completeness, uniqueness, domain bounds, and cross-table referential integrity. |
| **Backend API** | FastAPI, Uvicorn, SQLAlchemy 2.0, Psycopg 3 | High-throughput asynchronous REST API serving 12 domain endpoints with connection pooling and `NullPool` serverless compatibility. |
| **Frontend UI** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS | Enterprise executive dashboard featuring 9 operational pages, Recharts SVG visualizations, and global date-range filtering. |
| **Cloud Deployment** | Vercel (Frontend & Backend), Neon (PostgreSQL DW) | Fully serverless multi-project cloud deployment eliminating persistent VM hosting expenses. |
| **Quality & CI/CD** | Pytest (129 tests), ESLint, TypeScript Compiler | Automated testing enforcing 100% test passing, zero linting warnings, and strict type safety. |

---

## 8. Data Sources & Dataset Overview

The platform models the operations of a multi-facility distributor (*Nexa Distribution Group*) over calendar year 2025 (`2025-01-01` to `2025-12-31`):

| Domain | Dataset Source | Record Count | Business Description |
| :--- | :--- | :--- | :--- |
| **Sales** | `sales_transactions.csv` | 20,000 rows | Granular line-item sales across 8,053 customer invoices and 3 sales channels (In-Store, Online, Phone). |
| **Inventory** | `inventory_snapshots.csv` | 9,000 rows | Periodic inventory position snapshots across 300 unique SKU-warehouse site combinations. |
| **Procurement** | `purchase_orders.csv` | 1,000 POs (3,000 lines) | Purchase order lines capturing commitments, unit costs, vendor terms, and expected delivery dates. |
| **Goods Receipts** | `goods_receipts.csv` | 1,453 receipts | Dock receipt quality inspection events recording received quantity, accepted quantity, and late receipt flags. |
| **Expenses (OpEx)** | `operating_expenses.csv` | 2,000 expenses | Operational expenses across 6 standard corporate cost categories and 5 regional branches. |
| **Master Data** | `products`, `customers`, `suppliers`, `branches`, `warehouses` | 1,118 master entities | Dimensional master data capturing catalog pricing, customer classifications, supplier ratings, and facility geography. |

---

## 9. Data Warehouse Design & Dimensional Modeling

The Gold Data Warehouse implements an enterprise star schema optimized for slicing, dicing, and sub-50ms query rollups:

```
                              ┌────────────────────┐
                              │   gold.dim_date    │
                              │      730 rows      │
                              └─────────┬──────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
           ▼                            ▼                            ▼
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│  gold.dim_product  │        │  gold.fact_sales   │        │ gold.dim_customer  │
│      100 SKUs      │◄───────┤    20,000 lines    ├───────►│   1,000 accounts   │
└──────────┬─────────┘        └─────────┬──────────┘        └────────────────────┘
           │                            │
           │                            ▼
           │                  ┌────────────────────┐
           │                  │  gold.dim_branch   │
           │                  │       5 hubs       │
           │                  └─────────┬──────────┘
           │                            │
           ▼                            ▼
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│ bridge_prod_supp   │        │fact_inv_snapshot   │        │ gold.dim_warehouse │
│     150 links      │        │    9,000 rows      ├───────►│    3 facilities    │
└──────────┬─────────┘        └────────────────────┘        └────────────────────┘
           │                            ▲
           ▼                            │
┌────────────────────┐        ┌─────────┴──────────┐        ┌────────────────────┐
│ gold.dim_supplier  │◄───────┤fact_po_lines       │        │gold.dim_expense_cat│
│     10 vendors     │        │    3,000 lines     │        │    6 categories    │
└──────────┬─────────┘        └─────────┬──────────┘        └─────────┬──────────┘
           │                            │                             │
           ▼                            ▼                             ▼
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│ fact_goods_receipt │◄───────┤po_line_key lookup  │        │fact_operat_expenses│
│   1,453 receipts   │        │(Referential Link)  │        │    2,000 lines     │
└────────────────────┘        └────────────────────┘        └────────────────────┘
```

### Dimension & Bridge Tables
- **`gold.dim_product` (100 rows):** SKU code, product name, category (Electronics, Appliances, Home Goods), unit cost, base retail price.
- **`gold.dim_customer` (1,000 rows):** Customer name, segment (Corporate, Wholesale, Retail), credit limit, region.
- **`gold.dim_branch` (5 rows):** Regional hubs (Cairo, Giza, Alexandria, Tanta, Mansoura), manager, capacity.
- **`gold.dim_warehouse` (3 rows):** Regional distribution centers, square footage, logistics capabilities.
- **`gold.dim_supplier` (10 rows):** Active registered vendor profiles, country, performance scorecards, risk categories.
- **`gold.dim_date` (730 rows):** Complete calendar dimension (2024–2025) with year, quarter, month, day, day-of-week, weekend flags.
- **`gold.dim_expense_category` (6 rows):** Facilities, Salaries, Logistics, Marketing, IT & Systems, Administration.
- **`gold.bridge_product_supplier` (150 rows):** Resolves many-to-many relationships between multi-source products and certified vendors.
- **`gold.bridge_branch_warehouse` (15 rows):** Maps regional branches to their primary and secondary fulfillment distribution centers.

### Granular Fact Tables
- **`gold.fact_sales` (20,000 rows):** Grain = 1 line item per customer invoice. Captures quantity, unit price, discount amount, gross revenue, net revenue, cost of goods sold (COGS), and gross profit.
- **`gold.fact_inventory_snapshot` (9,000 rows):** Grain = 1 SKU per warehouse per snapshot date. Captures quantity on hand, reorder point, unit cost, inventory valuation, and binary stockout flags.
- **`gold.fact_purchase_order_lines` (3,000 rows):** Grain = 1 purchase order line item. Captures ordered quantity, unit cost, line total, delivery due date, and order status (Open, Received, Cancelled).
- **`gold.fact_goods_receipts` (1,453 rows):** Grain = 1 dock inspection delivery event. Captures received quantity, accepted quantity, rejected quantity, inspection duration, and late delivery flags.
- **`gold.fact_operating_expenses` (2,000 rows):** Grain = 1 operating expenditure entry per cost center per branch. Captures recorded date, expense amount, payment status, and budget variance.

---

## 10. Apache Airflow Orchestration

The end-to-end data pipeline is automated through the `opspulse_pipeline` DAG in **Apache Airflow 3.4.0**:

```
[Start Pipeline]
       │
       ▼
[Task Group: Bronze Ingestion] ──────► 12 parallel stream extraction tasks
       │
       ▼
[Task Group: Silver Cleansing] ──────► 12 parallel standardization & quarantine tasks
       │
       ▼
[Data Quality Gate Task]       ──────► Executes 210 validation assertions (Fail-Fast Gate)
       │
       ▼
[Task Group: Gold DW Loading]  ──────► Dimension loaders, bridge loaders, fact table loaders
       │
       ▼
[Observability & Telemetry]    ──────► Extracts task durations, volume lineage & failure logs
       │
       ▼
[End Pipeline]
```

### Pipeline Performance & Characteristics
- **Total Tasks:** 30 orchestrated tasks organized into modular TaskGroups.
- **Execution Speed:** Full pipeline completes in **28.32 seconds** across all 150,627 cumulative Medallion record observations.
- **Idempotency:** All loading operations utilize `ON CONFLICT` semantics or partitioned date boundaries to guarantee safe pipeline reruns without record duplication.
- **Automated Failure Classification:** Any task failure triggers an exception interceptor that classifies the failure (e.g., `SchemaMismatch`, `DataQualityViolation`, `NetworkTimeout`) and logs it into `monitoring.pipeline_task_metrics`.

---

## 11. Automated Data Quality Framework

OpsPulse enforces an uncompromising **Data Quality Gate** (`backend/src/validation/data_quality/`) that audits all Silver datasets prior to warehouse ingestion:

| Quality Dimension | Assertion Count | Production Pass Rate | Example Verified Constraint |
| :--- | :--- | :--- | :--- |
| **Completeness** | 48 checks | **100% (48/48)** | Mandatory non-null constraints on primary keys (`invoice_id`, `sku`), dates, and transaction totals. |
| **Uniqueness** | 32 checks | **100% (32/32)** | Unique natural keys (`customer_id`, `supplier_id`) and composite line identifiers (`order_id + line_number`). |
| **Validity** | 44 checks | **100% (44/44)** | Bounds validation (`discount_rate BETWEEN 0 AND 0.50`, `unit_price > 0`), valid email syntax, ISO timestamp conformance. |
| **Referential Integrity** | 24 checks | **100% (24/24)** | Parent-child relationship checks ensuring zero orphan sales lines, purchase orders, or dock receipts. |
| **Business Logic** | 62 checks | **100% (62/62)** | Cross-column formulas: `gross_amount == quantity * unit_price`, `accepted_qty <= received_qty`, `net_amount <= gross_amount`. |
| **Total Assertions** | **210 checks** | **100% Passed** | **Zero errors permitted in production warehouse.** |

```json
{
  "suite_execution_timestamp": "2026-11-15T05:28:45Z",
  "total_assertions_evaluated": 210,
  "passed_assertions": 210,
  "failed_assertions": 0,
  "quarantined_records_count": 0,
  "overall_data_quality_score": 100.0,
  "gate_decision": "PROCEED_TO_GOLD_LOAD"
}
```

---

## 12. Pipeline Observability & Lineage Telemetry

Data operations are observable in real time through dedicated PostgreSQL schemas:

### Telemetry Schemas in `opspulse_dw`
- **`monitoring.pipeline_run_metrics`:** Records pipeline batch ID, run trigger type (Scheduled vs Manual), overall execution duration, start/end timestamps, and success flags.
- **`monitoring.pipeline_task_metrics`:** Records individual task durations (seconds), task states, retry counts, and sanitized error traces.
- **`monitoring.pipeline_data_volume_metrics`:** Records Medallion layer record progression at each pipeline hop for batch isolation:
  $$\text{Raw: } 37,721 \longrightarrow \text{Bronze: } 37,721 \longrightarrow \text{Silver: } 37,721 \longrightarrow \text{Gold: } 37,464 \quad (\Sigma = 150,627 \text{ cumulative layer observations})$$

### Real-Time Observability Features
- **Layer-Level Volume Lineage:** Accurately accounts for data volume at each stage of the Medallion pipeline. In the verified pipeline run (`batch_20261115_051056_1d64c5da`), exactly 37,721 raw transactional records were ingested into Bronze and validated into Silver with zero quarantined records (`Quarantine = 0`). Gold loading modeled these events into 15 dimensional, bridge, and fact tables yielding 37,464 records due to dimensional deduplication and star-schema conformances (a combined total of 150,627 Medallion pipeline observations).
- **Isolated Quality Governance Metrics:** Data Quality assertion executions (210 checks executed, 100% pass rate) are persisted under `layer = 'DataQuality'` and tracked independently from physical entity volumes.
- **SLA Tracking:** Tracks execution against 60-second execution SLAs (average: 28.32 seconds).
- **Automated Root-Cause Classification:** Categorizes failures for automated alert routing without manual log trawling.

---

## 13. Backend API Architecture (FastAPI)

The backend (`backend/src/api/`) exposes a high-throughput, low-latency REST API serving the analytical dashboard:

- **Framework:** FastAPI running on Uvicorn with Pydantic v2 data models.
- **Connection Management:** SQLAlchemy 2.0 engine with Psycopg 3 binary driver. In serverless deployment (`VERCEL=1`), automatically detects runtime and configures `NullPool` with `pool_pre_ping=True`, preventing connection pool exhaustion on Neon PostgreSQL.
- **Security:** Parameterized SQL queries preventing injection, strict CORS whitelisting, and centralized exception handling preventing internal stack trace leaks.

### 12 Production REST Endpoints

| HTTP Method & Route | Domain | Description & Parameters |
| :--- | :--- | :--- |
| `GET /api/health` | Health | Warehouse connectivity ping, active database status, and uptime timestamp. |
| `GET /api/overview` | Executive | Top-level KPIs, 12-month revenue curve, branch performance, and top SKUs (`?quarter=1..4`). |
| `GET /api/sales` | Sales | Gross revenue, discounts, net sales, channel revenue breakdown, and quarterly trends. |
| `GET /api/sales/transactions` | Sales | Paginated transactional ledger supporting search, channel filtering, and quarter selection. |
| `GET /api/inventory` | Inventory | Facility capacity utilization, inventory valuation, dead stock metrics, and stockout rates. |
| `GET /api/inventory/items` | Inventory | Paginated SKU inventory ledger with warehouse filtering and stockout alert indicators. |
| `GET /api/procurement` | Procurement | Committed PO spend, open PO counts, vendor lead times, and dock OTIF delivery rates. |
| `GET /api/procurement/orders` | Procurement | Paginated purchase order registry with supplier filtering and status indicators. |
| `GET /api/suppliers` | Suppliers | Vendor scorecard directory with multi-fact pre-aggregated spend, quality ratings, and risk levels. |
| `GET /api/expenses` | Expenses | Operating expenditure ledger, monthly budget variance, and cost center distribution. |
| `GET /api/monitoring` | Monitoring | Real-time Airflow DAG execution history, task duration telemetry, and Medallion volume lineage. |
| `GET /api/data-quality` | Quality | 210 assertion test results, dataset health scores, and categorical quality breakdowns. |

---

## 14. Frontend Executive Dashboard (Next.js 14)

The executive web application (`frontend/`) delivers 9 data-dense, responsive operational views built with **Next.js 14 App Router, TypeScript, Tailwind CSS, and Recharts**:

### Dashboard Screen Showcase

| Screen | View Name | Key Capabilities & Visualizations | Screenshot |
| :---: | :--- | :--- | :---: |
| **01** | **Executive Overview** | Total Revenue (\$357.43M), Gross Profit (\$45.43M), Invoices (8,053), Revenue Trend, Branch Performance, Top SKUs. | ![Executive Overview](docs/screenshots/01_overview.png) |
| **02** | **Sales Analytics** | Channel Share (In-Store 34%, Phone 33%, Online 33%), Discount Analysis, Paginated Transaction Registry. | ![Sales Analytics](docs/screenshots/02_sales.png) |
| **03** | **Inventory Position** | Total Valuation (\$17.17M), Stockout Rate (18.0%), Warehouse Capacity Utilization, Low Stock Alert Ledger. | ![Inventory Position](docs/screenshots/03_inventory.png) |
| **04** | **Procurement & POs** | Open PO Commitments (\$360.56M), Fulfillment Rates, Supplier Lead Times, PO Status Ledger. | ![Procurement](docs/screenshots/04_procurement.png) |
| **05** | **Supplier Directory** | Vendor Scorecards, Spend Distribution (\$455.84M Total), On-Time Delivery Rates, Risk Classifications. | ![Supplier Directory](docs/screenshots/05_suppliers.png) |
| **06** | **Operating Expenses** | Annual OpEx (\$39.63M), Cost Category Breakdown, Branch Cost Allocation, Monthly Budget Variance. | ![Operating Expenses](docs/screenshots/06_expenses.png) |
| **07** | **Pipeline Observability** | Airflow DAG Telemetry, Task Duration Benchmarks (28.32s), Medallion Volume Lineage Tracking. | ![Pipeline Observability](docs/screenshots/07_monitoring.png) |
| **08** | **Data Quality Audit** | 210 Automated Assertions, Categorical Quality Scores (100% across all 5 dimensions), Health Matrix. | ![Data Quality Audit](docs/screenshots/08_data_quality.png) |
| **09** | **System Diagnostics** | Live PostgreSQL Connection Status, API Latency Diagnostics, Configurable Telemetry Refresh Intervals. | ![System Diagnostics](docs/screenshots/09_settings.png) |

---

## 15. Cloud Deployment Architecture (Vercel + Neon)

OpsPulse is architected for zero-maintenance, cost-effective cloud deployment using **Vercel** and **Neon PostgreSQL**:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           GitHub Repository                             │
│                     tharwat-farag/OpsPulse                              │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
         Root: frontend/                     Root: backend/
                    ▼                                 ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────┐
│         Vercel Project B              │ │        Vercel Project A       │
│           (Frontend)                  │ │           (Backend)           │
│  - Framework: Next.js 14 App Router   │ │  - Framework: FastAPI ASGI    │
│  - UI: Tailwind CSS, Recharts, Lucide │ │  - Runtime: Python Serverless │
│  - Proxy: rewrites /api/* to Backend  │ │  - Entrypoint: backend/main.py│
└───────────────────┬───────────────────┘ └───────────────┬───────────────┘
                    │                                     │
                    │ /api/* HTTPS rewrites               │ psycopg3 + NullPool
                    └────────────────────────────────────►│
                                                          ▼
                                          ┌───────────────────────────────┐
                                          │        Neon PostgreSQL        │
                                          │     (Cloud Data Warehouse)    │
                                          │  - gold.* (Star Schema)       │
                                          │  - monitoring.* (Telemetry)   │
                                          └───────────────────────────────┘
```

- **Frontend Project (Vercel):** Next.js 14 App Router configured with server-side API rewrites in `next.config.mjs`. Proxies `/api/*` to `BACKEND_API_URL` server-to-server, completely eliminating CORS restrictions, mixed-content warnings, and third-party cookie issues.
- **Backend Project (Vercel):** Zero-configuration FastAPI deployment using `backend/main.py` entrypoint. Scales to zero when idle with active CPU fluid compute.
- **Database (Neon PostgreSQL):** Serverless PostgreSQL instance storing `gold` and `monitoring` schemas. Automatically queried via `NullPool` to prevent connection leaks during serverless scale-outs.
- **Zero Third-Party VM Dependencies:** Render and persistent VM hosting are completely eliminated, achieving 100% serverless availability with zero standby costs.
- **Step-by-Step Deployment Guide:** Detailed setup instructions in [docs/vercel_deployment.md](docs/vercel_deployment.md).

---

## 16. Authoritative Business KPIs & Reconciliation

Every metric across the entire platform reconciles 100% against the underlying PostgreSQL warehouse:

| Metric Name | Authoritative Value | Source Formula & Definition | Verification Query |
| :--- | :--- | :--- | :--- |
| **Gross Sales Amount** | **$380,108,747.31** | $\sum (\text{quantity} \times \text{unit\_price})$ across 20,000 sales lines | `SELECT SUM(gross_amount) FROM gold.fact_sales;` |
| **Total Discounts** | **$22,681,878.26** | Total promotional price reductions deducted from sales | `SELECT SUM(discount_amount) FROM gold.fact_sales;` |
| **Net Sales Revenue** | **$357,426,869.05** | $\text{Gross Sales} - \text{Discounts}$ across 8,053 customer invoices | `SELECT SUM(net_amount) FROM gold.fact_sales;` |
| **Gross Profit** | **$45,431,649.88** | $\text{Net Revenue} - \text{COGS}$ (Gross Margin: **12.71%**) | `SELECT SUM(gross_profit) FROM gold.fact_sales;` |
| **Distinct Invoices** | **8,053 Invoices** | Average Order Value (AOV): **$44,384.31** | `SELECT COUNT(DISTINCT invoice_id) FROM gold.fact_sales;` |
| **Current Inventory Valuation** | **$17,169,853.11** | Latest snapshot valuation across 300 SKU-warehouse sites | `SELECT SUM(total_value) FROM gold.fact_inventory_snapshot WHERE snapshot_date = '2025-12-31';` |
| **Stockout Rate (Latest)** | **18.0%** | 54 out of 300 SKU locations currently out of stock | `SELECT (COUNT(CASE WHEN is_stockout THEN 1 END)::float / COUNT(*)) * 100 FROM gold.fact_inventory_snapshot WHERE snapshot_date = '2025-12-31';` |
| **Committed PO Spend (Open)** | **$360,560,754.34** | Contractually committed spend across 782 Open POs | `SELECT SUM(line_total) FROM gold.fact_purchase_order_lines WHERE status = 'Open';` |
| **Total Supplier PO Spend** | **$455,836,491.00** | Total purchase orders across all 10 active registered suppliers | `SELECT SUM(line_total) FROM gold.fact_purchase_order_lines;` |
| **Goods Receipt Acceptance Rate** | **95.7% (Avg)** | **95.7%** per-receipt average; **97.7%** aggregate accepted units | `SELECT AVG(acceptance_rate) * 100 FROM gold.fact_goods_receipts;` |
| **Dock On-Time Delivery Rate** | **32.9%** | Receipts delivered on or before promised delivery date | `SELECT (COUNT(CASE WHEN NOT is_late_receipt THEN 1 END)::float / COUNT(*)) * 100 FROM gold.fact_goods_receipts;` |
| **Total Operating Expenses (OpEx)** | **$39,631,974.10** | Full year 2025 operating expenditures (11.1% of Net Revenue) | `SELECT SUM(expense_amount) FROM gold.fact_operating_expenses;` |

*Complete mathematical definitions and edge-case reconciliations documented in [docs/business_metrics_dictionary.md](docs/business_metrics_dictionary.md).*

---

## 17. Testing, Quality Assurance & Verification

OpsPulse maintains rigorous test automation across every layer of the platform:

```bash
# 1. Run Complete Python Backend & Data Quality Test Suite
.venv\Scripts\pytest -v
# Result: 129 passed, 1 warning in 14.17s

# 2. Frontend TypeScript Strict Compilation Check
cd frontend
npm run type-check
# Result: 0 errors (tsc --noEmit)

# 3. Frontend ESLint Code Hygiene Check
npm run lint
# Result: ✔ No ESLint warnings or errors

# 4. Production Build Verification
npm run build
# Result: Compiled successfully; 12/12 static pages prerendered
```

### Test Suite Structure (`tests/`)
- **`test_api_endpoints.py`:** Tests all 12 analytical REST endpoints, query parameters, pagination, and error responses.
- **`test_business_rules.py`:** Validates cross-column financial and operational formulas.
- **`test_completeness.py` & `test_uniqueness.py`:** Verifies nullability and primary key uniqueness across datasets.
- **`test_referential.py` & `test_validity.py`:** Validates foreign key constraints and domain value bounds.
- **`test_monitoring_*.py`:** Validates observability telemetry collection, volume lineage extraction, and failure classifiers.
- **`test_replication_engine.py`:** Tests cloud warehouse replication, `OVERRIDING SYSTEM VALUE` identity column handling, and sequence synchronization.
- **`test_vercel_deployment.py`:** Tests Vercel zero-config FastAPI entrypoint (`backend/main.py`), root metadata (`GET /`), and `NullPool` serverless engine behavior.

---

## 18. Local Installation & Quickstart

### Prerequisites
- **Python 3.11+** (Python 3.13 recommended)
- **Node.js 18.x or 20.x**
- **PostgreSQL 15+** running locally on port 5432

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/tharwat-farag/OpsPulse.git
cd OpsPulse

# Create and activate virtual environment
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

# Edit .env to set your PostgreSQL connection string:
# OPSPULSE_DATABASE_URL=postgresql+psycopg://postgres:your_password@127.0.0.1:5432/opspulse_dw
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 4. Start the Application
You can launch both the backend API and frontend dashboard concurrently:

```powershell
# Windows PowerShell Launcher:
.\start_opspulse.ps1
```

Or run each service in separate terminal sessions:

```bash
# Terminal 1 — FastAPI Backend (Port 8000)
$env:PYTHONPATH="backend/src"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Next.js Frontend (Port 3000)
cd frontend
npm run dev
```

Visit [`http://localhost:3000`](http://localhost:3000) in your browser. Interactive API documentation is available at [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs).

---

## 19. Repository Structure

```text
OpsPulse/
├── airflow/
│   └── dags/
│       └── opspulse_pipeline.py              # 30-task Airflow 3.4.0 DAG definition
├── backend/
│   ├── main.py                               # Vercel FastAPI production entrypoint
│   ├── requirements.txt                      # Python dependencies (FastAPI, SQLAlchemy, etc.)
│   └── src/
│       ├── analytics/sql/                    # 23 parameterized analytical SQL queries
│       ├── api/                              # FastAPI application & domain routes
│       │   ├── database.py                   # Database connection dependencies
│       │   ├── main.py                       # Core FastAPI application & CORS configuration
│       │   └── routes/                       # 8 analytical route modules under /api
│       ├── data_generation/                  # Synthetic retail stream generator
│       ├── ingestion/                        # Bronze layer ingestion & batch manifests
│       ├── monitoring/                       # Observability collectors & failure classifiers
│       ├── transformation/                   # Silver layer cleansing & quarantine routing
│       ├── validation/data_quality/          # 210-assertion Data Quality engine
│       └── warehouse/                        # PostgreSQL DDL scripts & dimensional loaders
│           ├── db_connection.py              # Dynamic engine factory (NullPool / QueuePool)
│           ├── loaders/                      # Dimension & fact loaders with surrogate keys
│           └── sql/                          # DDL: 6 dimensions, 2 bridges, 5 facts
├── docs/                                     # Comprehensive architectural documentation
│   ├── architecture.md                       # Platform architectural specifications
│   ├── business-requirements.md              # Domain requirements & business context
│   ├── business_metrics_dictionary.md        # Definitive KPI calculation formulas
│   ├── day_7_data_quality.md                 # Data quality framework deep dive
│   ├── day_8_observability.md                # Pipeline observability & telemetry guide
│   ├── day_9_frontend.md                     # Next.js 14 design system & components
│   ├── day_10_live_integration.md            # Live integration & API consumption guide
│   ├── final_project_stabilization_report.md # Full audit & reconciliation report
│   ├── operational_runbook.md                # Maintenance & operational runbook
│   ├── screenshots/                          # Real application view screenshots (01–09)
│   └── vercel_deployment.md                  # Step-by-step Vercel + Neon cloud guide
├── frontend/                                 # Next.js 14 Enterprise Web Dashboard
│   ├── app/                                  # 9 Application page routes (App Router)
│   │   ├── page.tsx                          # Executive Overview (/ )
│   │   ├── sales/page.tsx                    # Sales Analytics (/sales)
│   │   ├── inventory/page.tsx                # Inventory Position (/inventory)
│   │   ├── procurement/page.tsx              # Procurement (/procurement)
│   │   ├── suppliers/page.tsx                # Supplier Directory (/suppliers)
│   │   ├── expenses/page.tsx                 # Operating Expenses (/expenses)
│   │   ├── monitoring/page.tsx               # Pipeline Observability (/monitoring)
│   │   ├── data-quality/page.tsx             # Data Quality Gate (/data-quality)
│   │   └── settings/page.tsx                 # System Diagnostics (/settings)
│   ├── components/                           # UI primitives, Recharts charts, and tables
│   ├── lib/                                  # API client, DateRange context, utilities
│   ├── next.config.mjs                       # Reverse-proxy API rewrite configuration
│   ├── package.json                          # Frontend dependencies
│   ├── tailwind.config.ts                    # Tailwind CSS configuration
│   └── tsconfig.json                         # Strict TypeScript configuration
├── scripts/
│   └── replicate_warehouse_to_cloud.py       # Safe resumable PostgreSQL cloud replication tool
├── tests/                                    # 129 automated unit and integration tests
├── .env.example                              # Multi-environment configuration template
├── .gitignore                                # Exclusions (.venv, .next, .vercel, data)
├── pytest.ini                                # Pytest test runner configuration
├── README.md                                 # Comprehensive portfolio documentation
└── start_opspulse.ps1                        # Concurrent local services launcher
```

---

## 20. Documentation Index & Deep Dives

For detailed architectural specifications, runbooks, and implementation reports, explore the dedicated documentation suite:

| Document | Focus & Content |
| :--- | :--- |
| **[Vercel Cloud Deployment Guide](docs/vercel_deployment.md)** | Complete step-by-step instructions for deploying Project A (FastAPI Backend), Project B (Next.js Frontend), and Neon PostgreSQL. |
| **[Business Metrics Dictionary](docs/business_metrics_dictionary.md)** | Authoritative definitions, SQL formulations, and business reconciliation for all 12 platform KPIs. |
| **[Platform Architecture Specification](docs/architecture.md)** | Deep-dive design specification covering Medallion data engineering, Kimball modeling, and data flow. |
| **[Data Quality Framework Guide](docs/day_7_data_quality.md)** | Technical breakdown of the 210 programmatic assertions, quarantine sink mechanisms, and pass/fail thresholds. |
| **[Pipeline Observability & Telemetry](docs/day_8_observability.md)** | Specifications for Medallion volume lineage tracking, task execution duration telemetry, and failure classifiers. |
| **[Frontend Design System & UX](docs/day_9_frontend.md)** | Overview of Next.js 14 App Router layout, Recharts visualization components, and global DateRange state management. |
| **[Operational Runbook & Maintenance](docs/operational_runbook.md)** | Disaster recovery, pipeline reprocessing, database backup routines, and production troubleshooting procedures. |
| **[Full Stabilization & Audit Report](docs/final_project_stabilization_report.md)** | Comprehensive evidence-based sign-off report covering data integrity reconciliation and end-to-end testing. |

---

## 21. License & Disclaimer

- **License:** This project is licensed under the [MIT License](LICENSE).
- **Synthetic Data Disclaimer:** All transactional records, customer names, vendor scorecards, addresses, and employee identities were synthetically generated using Python's `Faker` library for the fictional company *Nexa Distribution Group*. No real commercial or personally identifiable information (PII) is contained within this repository.
- **Calendar Boundary:** Transactional data spans calendar year 2025 (`2025-01-01` to `2025-12-31`). Queries outside this date range correctly return empty result sets.
