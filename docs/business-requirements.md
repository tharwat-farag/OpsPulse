# OpsPulse – Business Requirements Document (BRD)

**Project Name:** OpsPulse  
**Project Type:** Business Operations & Profitability Intelligence Platform  
**Industry Focus:** Retail & Distribution  
**Document Version:** 1.1  
**Document Status:** Updated – Implementation Progress Reflected

---

## 1. Project Overview

OpsPulse is a data-driven Business Operations & Profitability Intelligence Platform designed to help retail and distribution companies gain unified visibility into their operational and financial performance.

The platform brings together data from sales, inventory, procurement, suppliers, branches, and operating expenses to build a centralized analytical data foundation.

Through structured data processing, dimensional modeling, and business-focused analytics, OpsPulse aims to identify operational inefficiencies, highlight business risks, and support data-driven decision-making.

The project is being developed incrementally, starting with a local Data Engineering foundation before introducing cloud services and an interactive web application.

## 2. Business Problem

Retail and distribution companies often manage their operations using disconnected systems and data sources.

This creates several business challenges:

- Limited visibility into overall business performance.
- Difficulty monitoring product and branch profitability.
- Inventory shortages and excess stock.
- Inefficient inventory distribution across branches.
- Limited visibility into supplier performance.
- Incomplete procurement and delivery tracking.
- Time-consuming manual reporting.
- Inconsistent and unreliable business data.

These challenges can lead to operational inefficiencies, missed sales opportunities, and unnecessary costs.

OpsPulse addresses these challenges by establishing a unified data foundation and transforming operational data into meaningful business metrics.

## 3. Project Objectives

OpsPulse aims to:

1. Integrate operational data from multiple business domains.
2. Establish a unified and reliable analytical data foundation.
3. Implement structured Bronze, Silver, and Gold data layers.
4. Monitor sales, revenue, and profitability performance.
5. Identify inventory risks and stock distribution issues.
6. Evaluate supplier and procurement performance.
7. Track operating expenses and simplified operating results.
8. Apply data quality checks throughout the processing workflow.
9. Provide actionable business insights through analytical interfaces.
10. Support future cloud-based data engineering capabilities.

## 4. Target Business Environment

The initial simulated business is:

**Nexa Distribution Group**

A fictional retail and distribution company with the following characteristics:

| Business Component | Description |
|---|---|
| Branches | 5 |
| Warehouses | 3 |
| Products | 100 |
| Customers | 1,000 |
| Suppliers | 10 |
| Sales Channels | Multiple |
| Business Model | Retail & Distribution |

All datasets are synthetically generated for demonstration and testing purposes.

The company, its operational records, and its financial figures do not represent a real organization.

## 5. Target Users

### Executive Management
Needs an overview of business performance, profitability, operating expenses, and operational risks.

### Sales Managers
Need to monitor sales trends, revenue by branch, sales channels, and product profitability.

### Inventory Managers
Need to identify stock shortages, inventory availability, and stock distribution issues.

### Procurement Managers
Need to evaluate supplier performance, purchase orders, delivery timelines, and received quantities.

### Data and Technical Teams
Need to monitor data processing, data quality, pipeline execution, and analytical data availability.

## 6. Functional Requirements

The following table distinguishes implemented capabilities from planned application features.

| ID | Requirement | Description | Status |
|---|---|---|---|
| FR-01 | Data Integration | Generate and ingest operational datasets from CSV sources. | Implemented |
| FR-02 | Data Processing | Clean, validate, standardize, and transform data through Bronze and Silver layers. | Implemented |
| FR-03 | Sales Intelligence | Analyze revenue, gross profit, margins, sales trends, and branch performance using SQL. | Implemented |
| FR-04 | Inventory Intelligence | Analyze inventory snapshots, stock availability, inventory value, and stockout indicators. | Implemented |
| FR-05 | Procurement Intelligence | Analyze purchase orders, received quantities, supplier delivery performance, and purchase cost variance. | Implemented |
| FR-06 | Business Alerts | Detect predefined operational issues and generate user-facing alerts. | Planned |
| FR-07 | Recommendations | Provide rule-based business recommendations based on validated metrics. | Planned |
| FR-08 | Data Monitoring | Track ingestion manifests, processing results, and data quality validation. | Partially Implemented |
| FR-09 | Interactive Dashboard | Provide an interactive web interface for exploring business metrics. | Planned |

### Implementation Notes

- Current ingestion uses synthetically generated CSV datasets. Excel files and external APIs are not yet integrated.
- Bronze and Silver processing is implemented using Python and Pandas.
- The Gold analytical warehouse is implemented in PostgreSQL.
- Business analytics are implemented through SQL query files.
- Data validation and processing audit artifacts exist, while full orchestration and pipeline monitoring remain planned.
- FastAPI and the Next.js dashboard have not yet been implemented.

## 7. Key Business KPIs

### 7.1 Sales & Profitability

- Total Net Revenue
- Gross Profit
- Gross Profit Margin
- Sales Growth
- Revenue by Branch
- Revenue by Product
- Product Profitability
- Sales Channel Performance

**Current implementation:** Core sales and profitability analytics are available through SQL queries.

### 7.2 Inventory

- Latest Inventory Value
- Available Inventory Value
- Stockout Count
- Stockout Rate
- Inventory Turnover
- Days of Inventory
- Slow-Moving Inventory Value
- Excess Stock Value

**Current implementation:** Inventory snapshots, inventory value, availability, and stockout analytics are available. Inventory turnover, days of inventory, and advanced slow-moving/excess-stock analysis remain future enhancements.

Inventory value must be interpreted using the relevant inventory snapshot date. Historical snapshot values should not be added together and presented as current inventory value.

### 7.3 Procurement

- Supplier On-Time Delivery Rate
- Average Supplier Lead Time
- Purchase Order Fulfillment Rate
- Received Quantity
- Accepted Quantity
- Rejected Quantity
- Purchase Cost Variance

**Current implementation:** Supplier delivery, lead-time, goods-receipt, purchase-order fulfillment, and reference-price variance analytics are available.

The current supplier on-time delivery calculation is measured at the goods-receipt event level. Purchase order fulfillment is measured at the purchase-order-line level.

Purchase Cost Variance currently compares purchase costs against reference supplier prices, not verified historical contract prices.

### 7.4 Operating Expenses

- Total Operating Expenses
- Operating Expenses by Category
- Operating Expenses by Branch
- Simplified Operating Result

**Current implementation:** Operating expense analysis and branch-level profitability calculations are available.

The current Simplified Operating Result is calculated as:

**Gross Profit – Operating Expenses**

This is not a complete accounting net profit calculation.

### 7.5 Data Engineering

- Records Generated
- Records Ingested
- Records Processed
- Rejected Records
- Data Quality Validation Results
- Processing Batch Status
- Last Successful Processing Batch

**Current implementation:** Ingestion manifests, processing manifests, and Silver-layer audit results are available. Full pipeline execution monitoring and a user-facing monitoring interface remain planned.

## 8. Non-Functional Requirements

### Performance
Analytical SQL queries should provide efficient access to business metrics. The future dashboard should support responsive exploration of key indicators.

### Reliability
Processing failures and validation issues should be identifiable through structured processing and audit records.

### Data Quality
Data validation rules must be applied before publishing analytical datasets.

### Scalability
The architecture should support future increases in data volume, additional data sources, and cloud-based processing.

### Maintainability
The solution should use modular components with clearly separated responsibilities across ingestion, transformation, storage, analytics, and application layers.

### Security
Database credentials and sensitive configuration must be stored outside source code and must not be exposed in frontend code or public repositories.

## 9. MVP Scope

The MVP focuses on four operational domains:

1. Sales and Profitability.
2. Inventory Management.
3. Procurement Performance.
4. Data Engineering and Data Quality.

### Implemented Foundation

- Synthetic operational data generation.
- CSV data ingestion.
- Bronze and Silver data processing.
- Data validation and processing manifests.
- PostgreSQL analytical warehouse.
- Dimensional data modeling.
- Fact and dimension tables.
- SQL-based business analytics.
- Business KPI calculations.
- Profitability reconciliation.

### Planned Application and Platform Capabilities

- Full pipeline orchestration.
- Enhanced data quality monitoring.
- Microsoft Fabric and OneLake integration.
- PySpark-based cloud processing.
- FastAPI backend.
- Interactive Next.js dashboard.
- Business alerts and rule-based recommendations.

## 10. Technology Stack

| Component | Technology | Status |
|---|---|---|
| Programming | Python | Implemented |
| Data Processing | Pandas, NumPy | Implemented |
| Data Modeling | Dimensional Modeling, Star Schema | Implemented |
| Data Warehouse | PostgreSQL | Implemented |
| SQL Analytics | PostgreSQL SQL | Implemented |
| Containerization | Docker | Implemented |
| Data Quality | Python validation and audit checks | Partially Implemented |
| Testing | Pytest | Installed / Further tests planned |
| Cloud Data Platform | Microsoft Fabric | Planned |
| Cloud Storage | OneLake | Planned |
| Distributed Processing | PySpark | Planned |
| Orchestration | Fabric Data Factory | Planned |
| Backend | FastAPI | Planned |
| Frontend | Next.js, TypeScript | Planned |
| Visualization | Recharts | Planned |
| Version Control | Git and GitHub | In Progress |

## 11. Out of Scope

The following features are excluded from the initial MVP:

- Real-time streaming with Kafka.
- Artificial Intelligence chatbots.
- Predictive machine learning models.
- Mobile applications.
- Full ERP system replacement.
- Power BI dashboards.
- Production integration with real company systems.

## 12. Assumptions and Limitations

- All business data is synthetic and generated for demonstration purposes.
- The relationship between branches and warehouses includes an assumed mapping created for this simulated environment.
- Historical change handling for SCD Type 2 dimensions has not yet been fully implemented and validated.
- Inventory stockout indicators do not automatically represent confirmed lost sales.
- Supplier delivery performance and purchase fulfillment metrics use their explicitly defined analytical grains.
- Profitability calculations are simplified analytical measures and do not represent complete financial statements.
- Microsoft Fabric, OneLake, FastAPI, and the frontend dashboard are planned capabilities, not completed integrations.

## 13. Expected Business Value

OpsPulse is designed to help organizations:

- Improve operational visibility.
- Identify potential financial and operational risks.
- Improve inventory monitoring.
- Evaluate supplier performance.
- Understand branch and product profitability.
- Accelerate management reporting.
- Support more informed business decisions.

Business impact will be evaluated using simulated data and clearly identified estimates. No real financial savings or operational improvements will be claimed without measured evidence.

---

**Document Status:** Updated Business Requirements – Version 1.1  
**Project:** OpsPulse  
**Implementation Progress:** Data Engineering Foundation and SQL Analytics Completed (Days 1–5)