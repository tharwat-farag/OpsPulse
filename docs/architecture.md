# OpsPulse – System Architecture Document

**Project:** OpsPulse  
**Document Version:** 1.1  
**Architecture Status:** Local Data Engineering Foundation Implemented  
**Industry:** Retail & Distribution

---

## 1. Architecture Overview

OpsPulse follows a modular Data Engineering architecture designed to integrate operational data, process it through structured data layers, and deliver actionable business insights through an analytical platform.

The architecture separates data generation, ingestion, transformation, storage, analytical modeling, and application presentation.

The project is being developed incrementally, with a local Data Engineering foundation implemented first and cloud integration planned as a subsequent stage.

The architecture consists of two target execution environments:

- **Local Development Environment:** Implemented foundation using Python, Pandas, PostgreSQL, and Docker.
- **Microsoft Fabric Cloud Environment:** Planned cloud integration using OneLake, Fabric Lakehouse, PySpark, and Fabric Data Factory.

The local implementation provides the foundation for future cloud integration without making the core data warehouse dependent on cloud service availability.

## 2. Architecture Components

| Layer | Technology | Status | Responsibility |
|---|---|---|---|
| Data Sources | Synthetic CSV datasets | Implemented | Simulate retail operational data |
| Ingestion | Python, Pandas | Implemented | Extract and organize raw datasets |
| Bronze Storage | CSV, JSON manifests | Implemented | Preserve ingested source data and batch metadata |
| Silver Processing | Python, Pandas | Implemented | Clean, standardize, and validate datasets |
| Gold Warehouse | PostgreSQL | Implemented | Store dimensional analytical models |
| SQL Analytics | PostgreSQL SQL | Implemented | Calculate business KPIs and analytical results |
| Containerization | Docker | Implemented | Run the local PostgreSQL service |
| Testing | Pytest | Installed; test suite planned | Support automated testing |
| Cloud Storage | Microsoft OneLake | Planned | Provide unified cloud data storage |
| Cloud Processing | PySpark, Fabric Notebooks | Planned | Support scalable cloud transformations |
| Orchestration | Fabric Data Factory | Planned | Schedule and manage data pipelines |
| Backend | FastAPI | Planned | Expose business metrics through REST APIs |
| Frontend | Next.js, TypeScript | Planned | Deliver interactive dashboards |
| Visualization | Recharts | Planned | Display business metrics |

## 3. High-Level Data Flow

The currently implemented local data processing workflow:

1. Generate synthetic operational datasets using Python and Faker.
2. Validate generated source datasets.
3. Ingest raw CSV files into organized Bronze batches.
4. Preserve ingestion metadata and manifests.
5. Transform source datasets into the Silver layer using Pandas.
6. Apply validation rules and quarantine invalid records.
7. Audit the Silver layer.
8. Load dimensional models into PostgreSQL.
9. Execute SQL analytics against the Gold warehouse.
10. Reconcile business metrics across analytical outputs.

### Current Architecture Flow

```text
Synthetic Data Generation
          |
          v
      Raw CSV Data
          |
          v
   Python Ingestion
          |
          v
     Bronze Layer
   CSV + JSON Manifests
          |
          v
 Silver Transformation
    Python + Pandas
          |
          v
     Silver Layer
 Cleaned CSV Datasets
          |
          v
 PostgreSQL Loaders
          |
          v
   Gold Data Warehouse
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
       FastAPI
          |
          v
   Next.js Dashboard
          |
          v
   Business Users
```

The application flow will be implemented in later development stages.

## 4. Medallion Architecture

OpsPulse implements the Medallion Architecture to organize data processing into three logical layers: Bronze, Silver, and Gold.

### 4.1 Bronze Layer

**Purpose:** Preserve ingested source data and maintain ingestion traceability.

Responsibilities:

- Store raw source datasets.
- Organize data by ingestion batch.
- Preserve original source records.
- Maintain ingestion timestamps and metadata.
- Generate ingestion manifests.
- Support traceability and reprocessing.

**Implemented Storage Format:**
- CSV source datasets.
- JSON ingestion manifests.

### 4.2 Silver Layer

**Purpose:** Provide cleaned, standardized, and validated datasets.

Responsibilities:

- Validate required columns and data types.
- Handle missing and invalid values.
- Detect duplicate records.
- Standardize data structures.
- Validate business identifiers.
- Apply cross-field and business consistency rules.
- Separate invalid records through quarantine handling.
- Produce transformation manifests.

**Implemented Processing Technology:**
- Python
- Pandas

**Implemented Storage Format:**
- CSV datasets.

### 4.3 Gold Layer

**Purpose:** Provide business-ready analytical models for reporting and business intelligence.

Responsibilities:

- Implement dimensional data models.
- Maintain fact and dimension relationships.
- Support analytical queries.
- Calculate reusable business metrics.
- Enable business-level aggregations.
- Support profitability and operational analysis.

**Implemented Storage Technology:**
- PostgreSQL.

The Gold layer is implemented as a relational dimensional warehouse rather than a separate collection of Parquet files.

## 5. Data Warehouse Architecture

OpsPulse uses dimensional modeling based on the Star Schema approach.

The warehouse is implemented in PostgreSQL with separate schemas for:

- `staging`: Temporary and intermediate loading structures.
- `gold`: Analytical fact, dimension, and bridge tables.
- `audit`: Reserved for audit-related structures.

### 5.1 Dimension Tables

The warehouse contains eight dimensions:

| Dimension | Description |
|---|---|
| dim_date | Calendar and date attributes |
| dim_product | Product attributes |
| dim_customer | Customer attributes |
| dim_branch | Business branch attributes |
| dim_warehouse | Warehouse attributes |
| dim_supplier | Supplier attributes |
| dim_sales_channel | Sales channel classification |
| dim_expense_category | Operating expense classification |

### 5.2 Fact Tables

The warehouse contains five fact tables:

| Fact Table | Grain |
|---|---|
| fact_sales | One sales line |
| fact_inventory_snapshot | One product, warehouse, and snapshot date combination |
| fact_purchase_order_lines | One purchase order line |
| fact_goods_receipts | One goods receipt event |
| fact_operating_expenses | One operating expense transaction |

Each fact table has a defined grain to support accurate aggregations and prevent double counting.

### 5.3 Bridge Tables

Two bridge tables support business relationships:

- `bridge_product_supplier`: Represents product-to-supplier relationships and associated purchasing attributes.
- `bridge_branch_warehouse`: Represents branch-to-warehouse mappings.

The branch-to-warehouse mapping is a documented synthetic project assumption because the original source datasets do not provide this relationship.

### 5.4 Slowly Changing Dimensions

The following dimensions use a Type 2 structure:

- dim_product
- dim_customer
- dim_branch
- dim_supplier
- dim_warehouse

The current implementation establishes baseline dimension versions with validity periods and current-record indicators.

Historical version creation following changes in source attributes remains to be implemented and tested.

## 6. Backend Architecture

**Planned Technology:** Python + FastAPI.

The backend will act as the application service layer between the analytical warehouse and the frontend.

Planned responsibilities:

- Retrieve business metrics from PostgreSQL.
- Provide REST API endpoints.
- Apply business calculation rules.
- Support date and business filters.
- Generate operational alerts.
- Provide rule-based recommendations.
- Expose pipeline monitoring information.

The frontend will access analytical data through backend APIs rather than connecting directly to the database.

**Implementation Status:** Not yet implemented.

## 7. Frontend Architecture

**Planned Technology:** Next.js + TypeScript + Tailwind CSS + Recharts.

The web application will provide five main modules:

1. Executive Overview.
2. Sales Intelligence.
3. Inventory Intelligence.
4. Procurement Intelligence.
5. Data Pipeline Health.

Planned interface capabilities:

- Interactive KPI cards.
- Analytical charts.
- Date and branch filters.
- Product and supplier analysis.
- Inventory alerts.
- Business performance comparisons.
- Pipeline monitoring information.

Power BI is not part of the application architecture.

**Implementation Status:** Not yet implemented.

## 8. Cloud Architecture

Microsoft Fabric is the target cloud data platform for a future implementation stage.

Planned components:

| Component | Technology | Responsibility |
|---|---|---|
| Unified Storage | OneLake | Store cloud analytical data |
| Data Lakehouse | Fabric Lakehouse | Organize Bronze and Silver datasets |
| Processing | Fabric Notebooks, PySpark | Perform cloud transformations |
| Data Warehouse | Fabric Warehouse | Host analytical dimensional models |
| Orchestration | Fabric Data Factory | Schedule and manage pipelines |

Azure Data Lake Storage Gen2 may be integrated if an external cloud storage landing zone is required.

Cloud integration depends on workspace availability, permissions, and resource costs.

The current local PostgreSQL warehouse remains the implemented analytical foundation.

**Implementation Status:** Planned.

## 9. Local Development Architecture

The implemented local foundation uses:

- Python 3.13 for data generation, ingestion, and transformation.
- Pandas for data processing.
- Faker for synthetic data generation.
- PostgreSQL for the analytical warehouse.
- SQLAlchemy and Psycopg for database connectivity.
- Docker for the PostgreSQL service.
- Git for version control.

Additional planned local application components:

- FastAPI for backend services.
- Next.js for frontend development.
- Pytest for automated test coverage.

The local architecture is designed to operate independently of cloud service availability.

## 10. Data Quality and Monitoring

Data quality is applied throughout the implemented data processing workflow.

### Implemented Quality Checks

- Required column validation.
- Data type validation.
- Primary key uniqueness.
- Duplicate record detection.
- Referential integrity checks.
- Business rule validation.
- Quantity and financial consistency checks.
- Date and range validation.
- Quarantine handling for invalid records.
- Silver layer audit.

The warehouse loading process also validates dimensional relationships and fact table grain.

### Planned Monitoring Capabilities

Future monitoring components will track:

- Pipeline execution history.
- Pipeline success and failure status.
- Records processed and rejected.
- Data quality results.
- Processing errors.
- Last successful pipeline execution.

A complete automated orchestration and monitoring framework has not yet been implemented.

## 11. Security Architecture

The project follows basic security principles:

- Environment variables for database configuration.
- No hardcoded database credentials.
- No database credentials in frontend code.
- Backend-controlled database access.
- Input validation for future API requests.
- Exclusion of local environment files from version control.
- Restricted access to sensitive resources.

The PostgreSQL connection is currently configured through the `OPSPULSE_DATABASE_URL` environment variable.

## 12. Deployment Strategy

The initial development environment uses local Python processing and a Docker-based PostgreSQL service.

Future deployment stages will include:

- Independently deployable backend and frontend services.
- Containerized application components.
- Automated testing.
- Cloud data platform integration.
- Deployment configuration and environment management.

The final deployment architecture will be established after application integration and testing.

## 13. Architecture Principles

OpsPulse follows these principles:

1. Separation of concerns.
2. Modular application design.
3. Reusable data transformations.
4. Scalable data processing.
5. Data quality by design.
6. Clear data lineage.
7. Cloud portability where practical.
8. Business-driven technology selection.
9. Explicit data modeling and grain definition.
10. Transparent documentation of assumptions and limitations.

---

**Document Status:** Updated Architecture – Version 1.1

**Project:** OpsPulse

**Current Milestone:** Day 5 – SQL Analytics and Business KPIs Completed