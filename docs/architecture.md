
# OpsPulse – System Architecture Document

## 1. Architecture Overview

OpsPulse follows a modular, cloud-ready data architecture designed to integrate operational data, process it through structured data layers, and deliver actionable business intelligence through a web application.

The architecture separates data ingestion, storage, processing, analytics, backend services, and frontend presentation.

The system supports two execution environments:

- Local Development Environment
- Microsoft Fabric Cloud Environment

## 2. Architecture Components

| Layer | Technology | Responsibility |
|---|---|---|
| Data Sources | CSV, Excel, APIs | Provide operational data |
| Ingestion | Python | Extract and load source data |
| Cloud Orchestration | Fabric Data Factory | Schedule and manage pipelines |
| Storage | OneLake | Store lakehouse data |
| Processing | Python, Pandas, PySpark | Clean and transform data |
| Data Warehouse | PostgreSQL / Fabric Warehouse | Store analytical models |
| Backend | FastAPI | Expose business data through APIs |
| Frontend | Next.js, TypeScript | Deliver interactive dashboards |
| Visualization | Recharts | Display business metrics |
| Testing | Pytest | Validate application and data quality |
| Containerization | Docker | Provide consistent environments |

## 3. High-Level Data Flow

The main data processing workflow:

1. Extract data from operational sources.
2. Load raw records into the Bronze layer.
3. Validate and clean incoming data.
4. Transform data into the Silver layer.
5. Build analytical models in the Gold layer.
6. Load dimensional models into the data warehouse.
7. Calculate business KPIs.
8. Expose analytical results through FastAPI.
9. Display business insights through the Next.js dashboard.

## 4. Medallion Architecture

OpsPulse implements the Medallion Architecture.

### 4.1 Bronze Layer

Purpose: Preserve source data in its original structure.

Responsibilities:

- Store raw source records.
- Preserve ingestion timestamps.
- Maintain source identification.
- Support data traceability.

Storage Format: CSV and Parquet.

### 4.2 Silver Layer

Purpose: Provide clean and standardized datasets.

Responsibilities:

- Handle missing values.
- Remove duplicate records.
- Standardize data types.
- Validate business identifiers.
- Apply data consistency rules.
- Handle invalid records.

Storage Format: Parquet.

### 4.3 Gold Layer

Purpose: Provide business-ready analytical datasets.

Responsibilities:

- Build dimensional data models.
- Calculate reusable business metrics.
- Prepare datasets for analytical queries.
- Support dashboard reporting.

Storage Format: Parquet and analytical warehouse tables.

## 5. Data Warehouse Architecture

OpsPulse uses dimensional modeling based on the Star Schema approach.

### Dimension Tables

- dim_date
- dim_product
- dim_branch
- dim_warehouse
- dim_supplier
- dim_sales_channel

### Fact Tables

- fact_sales
- fact_inventory_snapshot
- fact_purchase_orders
- fact_operational_expenses

Each fact table will have a clearly defined grain to ensure accurate aggregations and prevent double counting.

## 6. Backend Architecture

Technology: Python + FastAPI.

The backend acts as the application service layer between the analytical warehouse and the frontend.

Responsibilities:

- Retrieve business metrics.
- Provide REST API endpoints.
- Apply business rules.
- Generate operational alerts.
- Generate rule-based recommendations.
- Handle filtering and date parameters.
- Provide pipeline monitoring information.

The frontend will access business data exclusively through backend APIs.

## 7. Frontend Architecture

Technology: Next.js + TypeScript + Tailwind CSS + Recharts.

The web application will provide the following modules:

1. Executive Overview.
2. Sales Intelligence.
3. Inventory Intelligence.
4. Procurement Intelligence.
5. Data Pipeline Health.

The interface will support interactive filters, analytical charts, KPI cards, operational alerts, and business recommendations.

Power BI is not part of the application architecture.

## 8. Cloud Architecture

Microsoft Fabric is the target cloud data platform.

Planned components:

- OneLake for unified data storage.
- Fabric Lakehouse for Bronze and Silver datasets.
- Fabric Notebooks for PySpark transformations.
- Fabric Warehouse for dimensional analytical models.
- Fabric Data Factory for pipeline orchestration.

Azure Data Lake Storage Gen2 may be integrated when an external cloud storage landing zone is required.

Cloud integration will depend on workspace availability, permissions, and resource costs.

## 9. Local Development Architecture

The initial MVP will run locally using:

- Python for ingestion and transformation.
- PostgreSQL for the analytical warehouse.
- Docker for containerized services.
- FastAPI for backend APIs.
- Next.js for frontend development.
- Pytest for automated testing.

This environment will allow the core application to operate independently of cloud service availability.

## 10. Data Quality and Monitoring

Data quality checks will be applied throughout the processing workflow.

Examples:

- Primary key uniqueness.
- Null value validation.
- Referential integrity.
- Data type validation.
- Negative quantity detection.
- Business rule validation.

Monitoring tables will track:

- Pipeline execution history.
- Ingestion logs.
- Data quality results.
- Rejected records.
- Processing errors.

## 11. Security Architecture

The system will follow basic security principles:

- Environment variables for configuration.
- No hardcoded credentials.
- No database credentials in frontend code.
- Backend-controlled database access.
- Input validation for API requests.
- Restricted access to sensitive resources.

## 12. Deployment Strategy

The initial development environment will use Docker and local services.

The frontend and backend will be independently deployable.

The cloud data platform will be integrated as a separate data infrastructure component.

The deployment architecture will be finalized after the MVP integration and testing stages.

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

---

**Document Status:** Initial Architecture – Version 1.0

**Project:** OpsPulse
    