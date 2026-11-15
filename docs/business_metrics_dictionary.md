# OpsPulse — Business Metrics Dictionary

This document serves as the authoritative enterprise reference for all operational, financial, inventory, procurement, and data quality metrics computed by the OpsPulse Data Engineering & Intelligence Platform.

---

## 1. Executive Overview & Sales Metrics

### 1.1 Gross Sales Amount
- **Business Meaning:** Total unadjusted transaction value of merchandise sales prior to discounts and promotional concessions across all sales channels.
- **Calculation Formula:**  
  $$\text{Gross Sales} = \sum (\text{gross\_amount}) = \sum (\text{quantity} \times \text{unit\_price})$$
- **Source Table:** `gold.fact_sales` join `gold.dim_date`
- **Grain:** Transaction sales line item (`sales_line_id`).
- **Relevant Filters:** `dim_date.year_number = 2025`, optional `quarter_number` (1-4).
- **Verified 2025 Baseline:** **$380,108,747.31** (Total Discounts deducted: **$22,681,878.26**).
- **Reconciliation Note:** Net Sales Revenue ($357,426,869.05) is Gross Sales minus Discounts. An earlier report draft cited $397.06M due to an erroneous textual addition of Net Revenue ($357.43M) + OpEx ($39.63M); the database and API have always computed and returned $380,108,747.31.

### 1.2 Total Net Sales Revenue
- **Business Meaning:** Gross value of all fulfilled merchandise sales less discounts and promotional concessions across all sales channels.
- **Calculation Formula:**  
  $$\text{Net Revenue} = \sum (\text{net\_revenue}) = \sum (\text{gross\_amount} - \text{discount\_amount})$$
- **Source Table:** `gold.fact_sales` join `gold.dim_date`
- **Grain:** Transaction sales line item (`sales_line_id`).
- **Relevant Filters:** `dim_date.year_number = 2025`, optional `quarter_number` (1-4).
- **Verified 2025 Baseline:** **$357,426,869.05** (across 20,000 transaction lines).
- **Known Limitations:** Returns/refund deductions are reflected at invoice level; zero quarantined sales lines exist in 2025.

### 1.3 Gross Profit & Gross Margin %
- **Business Meaning:** Operating profitability remaining after deducting standard product cost of goods sold (COGS).
- **Calculation Formula:**  
  $$\text{Gross Profit} = \sum (\text{gross\_profit}) = \sum (\text{net\_revenue} - \text{total\_cost})$$  
  $$\text{Gross Margin \%} = \left( \frac{\text{Gross Profit}}{\text{Net Revenue}} \right) \times 100$$
- **Source Table:** `gold.fact_sales` join `gold.dim_product`
- **Grain:** Transaction sales line item.
- **Verified 2025 Baseline:** **$45,431,649.88** (12.71% margin).

### 1.4 Total Invoices & Average Order Value (AOV)
- **Business Meaning:** Total count of distinct customer purchasing orders (invoices) and the average net spend per invoice.
- **Calculation Formula:**  
  $$\text{Total Invoices} = \text{COUNT(DISTINCT invoice\_id)}$$  
  $$\text{AOV} = \frac{\text{Total Net Revenue}}{\text{Total Invoices}}$$
- **Source Table:** `gold.fact_sales`
- **Grain:** Header-level invoice (`invoice_id`).
- **Verified 2025 Baseline:** **8,053 invoices** (AOV: **$44,384.31**).
- **Important Distinction:** Sales lines (20,000) represent items within invoices; distinct invoice count is 8,053.

### 1.5 Sales Channel Share
- **Business Meaning:** Net revenue and volume distribution across sales channels (`In-Store`, `Online`, `Phone`).
- **Calculation Formula:**  
  $$\text{Channel Share \%} = \left( \frac{\sum_{\text{channel}} \text{net\_revenue}}{\sum_{\text{total}} \text{net\_revenue}} \right) \times 100$$
- **Source Table:** `gold.fact_sales` join `gold.dim_sales_channel`
- **Grain:** Channel key (`sales_channel_key`).

### 1.6 Branch Performance & Regional Fulfillment
- **Business Meaning:** Regional revenue velocity across 5 physical branch hubs against their annual operating sales targets ($70.0M per branch).
- **Calculation Formula:**  
  $$\text{Target Achievement \%} = \left( \frac{\sum_{\text{branch}} \text{net\_revenue}}{\$70,000,000.00} \right) \times 100$$
- **Source Table:** `gold.fact_sales` join `gold.dim_branch`
- **Grain:** Branch key (`branch_key`).
- **Verified 2025 Branches:** `Mansoura Branch` ($72.5M), `Tanta Branch` ($71.9M), `Alexandria Branch` ($71.8M), `Cairo Branch` ($71.2M), `Giza Branch` ($69.9M).

---

## 2. Inventory & Warehouse Logistics Metrics

### 2.1 Current Inventory Valuation
- **Business Meaning:** Capital value of all merchandise on hand across distribution centers evaluated at standard cost.
- **Calculation Formula:**  
  $$\text{Inventory Value} = \sum (\text{total\_inventory\_value}) = \sum (\text{quantity\_on\_hand} \times \text{standard\_cost})$$
- **Source Table:** `gold.fact_inventory_snapshot`
- **Grain:** Product-Warehouse snapshot record at `date_key = MAX(date_key)` (2025-12-31).
- **Verified Baseline:** **$17,169,853.11** across 300 active SKU-warehouse locations (100 SKUs × 3 warehouses).
- **Known Limitations:** Must always evaluate `WHERE date_key = (SELECT MAX(date_key))` to prevent summing cumulative historical snapshots.

### 2.2 Stockout Rate
- **Business Meaning:** Percentage of SKU-warehouse locations with zero inventory available on hand.
- **Calculation Formula:**  
  $$\text{Stockout Rate \%} = \left( \frac{\text{COUNT}(\text{is\_stockout = TRUE})}{\text{Total SKU-Warehouse Locations}} \right) \times 100$$
- **Source Table:** `gold.fact_inventory_snapshot`
- **Grain:** SKU location at latest snapshot date.
- **Verified Baseline:** **18.0%** (54 out-of-stock locations out of 300).
- **Operational Interpretation:** A downward trend represents improved product availability and reduced customer fulfillment loss.

### 2.3 Warehouse Capacity Utilization
- **Business Meaning:** Ratio of cubic or square footage utilized by stored inventory relative to certified warehouse design capacity.
- **Calculation Formula:**  
  $$\text{Capacity Utilization \%} = \left( \frac{\sum \text{quantity\_on\_hand}}{\text{capacity\_units}} \right) \times 100$$
- **Source Table:** `gold.fact_inventory_snapshot` join `gold.dim_warehouse`
- **Grain:** Warehouse site (`warehouse_id`).
- **Verified Baseline Facilities:** `Cairo Main Warehouse` (83.5%), `Giza Main Warehouse` (77.2%), `Alexandria Main Warehouse` (74.6%).

---

## 3. Procurement & Supplier Performance Metrics

### 3.1 Committed Purchase Order Spend
- **Business Meaning:** Total contractually committed expenditures across open purchase orders issued to active registered suppliers.
- **Calculation Formula:**  
  $$\text{Committed Spend} = \sum (\text{line\_total}) \quad \text{WHERE order\_status IN ('Pending', 'Partially Received')}$$
- **Source Table:** `gold.fact_purchase_order_lines`
- **Grain:** PO Line item.
- **Verified Baseline:** **$360,560,754.34** across **782 distinct open purchase orders**.
- **Total PO Population:** 1,000 distinct POs (3,000 lines, \$455,836,491.34 total committed value):
  - Pending: 52 POs (\$19.2M)
  - Partially Received: 730 POs (\$341.3M)
  - Fully Received: 161 POs (\$68.4M)
  - Cancelled: 57 POs (\$26.8M)

### 3.2 Supplier On-Time In-Full (OTIF) Delivery Rate
- **Business Meaning:** Percentage of received shipments arriving at or before the scheduled delivery date meeting quality acceptance standards.
- **Calculation Formula:**  
  $$\text{OTIF \%} = \left( \frac{\text{COUNT}(\text{is\_late\_receipt = FALSE})}{\text{Total Goods Receipts}} \right) \times 100$$
- **Source Table:** `gold.fact_goods_receipts`
- **Grain:** Goods receipt record.
- **Verified Baseline:** **94.2%** (across 1,453 goods receipt deliveries).

### 3.3 Average Supplier Lead Time
- **Business Meaning:** Average number of business days elapsed between initial purchase order placement and dock warehouse delivery receipt.
- **Calculation Formula:**  
  $$\text{Avg Lead Time} = \text{AVG}(\text{receipt\_date} - \text{order\_date}) = \text{AVG}(\text{days\_from\_order})$$
- **Source Table:** `gold.fact_goods_receipts`
- **Verified Baseline:** **8.4 business days**.

### 3.4 Goods Receipt Acceptance Rate
- **Business Meaning:** Percentage of delivered merchandise units meeting quality standards and accepted into inventory upon dock arrival.
- **Calculation Formula:**  
  $$\text{Avg Per-Receipt Acceptance Rate \%} = \text{AVG}(\text{acceptance\_rate}) \times 100$$  
  $$\text{Aggregate Acceptance Rate \%} = \left( \frac{\sum \text{accepted\_qty}}{\sum \text{received\_qty}} \right) \times 100$$
- **Source Table:** `gold.fact_goods_receipts`
- **Grain:** Goods receipt record (`receipt_id`).
- **Verified Baseline:** **95.7%** average per receipt (**97.7%** aggregate units: 48,048 accepted out of 49,184 received across 1,453 goods receipts).
- **Unit Fraction Conversion:** The underlying database column `acceptance_rate` stores a fractional decimal between 0.0000 and 1.0000. Calculations must multiply by 100 prior to rounding to 1 decimal place to prevent truncation to 1.0%.

---

## 4. Operating Expenses (OpEx) Metrics

### 4.1 Total Operating Expenses
- **Business Meaning:** Total corporate and operational overhead expenditures incurred to operate the retail distribution network.
- **Calculation Formula:**  
  $$\text{Total OpEx} = \sum (\text{amount})$$
- **Source Table:** `gold.fact_operating_expenses` join `gold.dim_date`
- **Grain:** Expense transaction record.
- **Verified 2025 Baseline:** **$39,631,974.00** (across 2,000 expense records).
- **Categories:** Salaries & Wages ($18.6M, 46.9%), Facility Rent ($13.1M, 33.0%), Logistics & Freight ($8.0M, 20.1%).

### 4.2 OpEx to Net Revenue Ratio
- **Business Meaning:** Overhead efficiency ratio expressing operating expenses as a percentage of top-line net revenue.
- **Calculation Formula:**  
  $$\text{OpEx Ratio \%} = \left( \frac{\text{Total Operating Expenses}}{\text{Total Net Sales Revenue}} \right) \times 100$$
- **Verified 2025 Baseline:** **11.1%** (well within the corporate governance efficiency threshold of < 20.0%).

---

## 5. Pipeline Observability & Data Quality Metrics

### 5.1 Pipeline Execution Telemetry
- **Source:** PostgreSQL `monitoring.pipeline_run_metrics` and `monitoring.pipeline_task_metrics`.
- **Primary Entities:**
  - `total_duration_seconds`: Wall-clock execution time for DAG `opspulse_pipeline`.
  - `task_success_rate`: Percentage of DAG tasks completing with status `success` (30/30 tasks = 100%).
  - `record_lineage_count`: Volume transition across Medallion layers (Raw: 150,627 -> Bronze: 150,627 -> Silver: 150,627 -> Gold: 150,627).

### 5.2 Automated Data Quality Gates
- **Source:** Authoritative report artifact `data/quality_reports/latest_quality_report.json`.
- **Primary Assertions:**
  - Total Checks: **210 executed assertions** across 12 Silver datasets.
  - Overall Score: **100.0%** (210 Passed, 0 Failed, 0 Warnings).
  - Categorical Breadth: Completeness (48), Uniqueness (32), Validity (44), Referential Integrity (24), Business Logic Rules (62).
