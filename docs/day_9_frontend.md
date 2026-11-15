# OpsPulse — Day 9: Frontend Foundation & Dashboard UI

## 1. Overview & Architectural Objectives

OpsPulse Day 9 establishes the modern enterprise frontend foundation for the **Retail & Distribution Business Operations Intelligence Platform**.

Built using **Next.js 14 App Router**, **TypeScript**, **Tailwind CSS**, **Recharts**, and **Lucide React**, the frontend provides an executive-grade user interface for monitoring sales performance, warehouse inventory health, procurement workflows, operating expenses, pipeline observability, and automated data quality gates.

### Core Architectural Decisions
1. **Strict Decoupling from Backend Infrastructure**:
   - The frontend resides entirely within `frontend/` without touching backend Python modules, PostgreSQL schemas, or Airflow DAG configurations.
   - Demonstration datasets reside in structured, typed mock files (`lib/mock-data/`) clearly tagged as demo data and isolated from production data structures.
2. **Prepared API Abstraction Layer**:
   - `lib/api/client.ts` implements strongly typed response contracts (`ApiResponse<T>`) designed to plug into future FastAPI / GraphQL endpoints without refactoring UI components.
3. **Enterprise Design System**:
   - Premium dark navy sidebar (`#0F172A`, `#0B1120`) paired with a clean, high-clarity slate-50 workspace (`#F8FAFC`).
   - Restrained, intentional accent palette (Brand Blue `#2563EB`, Emerald `#10B981` for gains/pass states, Amber `#F59E0B` for low-stock/warnings, Rose `#EF4444` for defects/over-budget).
   - High information density with zero decorative noise or excessive animations.
4. **Interactive Component Architecture**:
   - Interactive date range picker with live state options (`Today`, `7d`, `30d`, `month`, `quarter`).
   - Dynamic search filters, category selectors, and column sorting on all tabular views.
   - Interactive SVG chart tooltips with currency and percentage formatting.
   - Responsive drawer navigation for mobile, tablet, and desktop viewports.

---

## 2. Directory Structure

```text
frontend/
├── app/
│   ├── globals.css                # Enterprise design tokens & scrollbar styles
│   ├── layout.tsx                 # Root layout with HTML/body scaffolding
│   ├── page.tsx                   # Overview Dashboard (/)
│   ├── sales/page.tsx             # Sales & Revenue Analytics (/sales)
│   ├── inventory/page.tsx         # Inventory & Fulfillment (/inventory)
│   ├── procurement/page.tsx       # Procurement & PO Tracking (/procurement)
│   ├── suppliers/page.tsx         # Supplier Performance Directory (/suppliers)
│   ├── expenses/page.tsx          # Operating Expenses & Variances (/expenses)
│   ├── monitoring/page.tsx        # Pipeline Observability & Run Analytics (/monitoring)
│   ├── data-quality/page.tsx      # Automated Data Quality Framework (/data-quality)
│   └── settings/page.tsx          # Platform Configuration & Runtime Diagnostics (/settings)
├── components/
│   ├── charts/
│   │   ├── BranchBarChart.tsx         # Horizontal branch revenue comparison
│   │   ├── ChannelSharePieChart.tsx   # Sales channel donut chart with legend
│   │   ├── ExpensesTrendChart.tsx     # Monthly actual vs. budget comparison
│   │   ├── RevenueTrendChart.tsx      # Area chart with revenue target & cost curves
│   │   └── VolumeLineageChart.tsx     # Medallion layer record lineage chart
│   ├── dashboard/
│   │   ├── ActivityFeed.tsx           # Operational event timeline
│   │   └── PipelineStatusWidget.tsx   # Live Airflow 3.4.0 DAG status summary
│   ├── layout/
│   │   ├── AppLayout.tsx              # Shell coordinating Sidebar, TopNav, and workspace
│   │   ├── Sidebar.tsx                # Enterprise dark navy navigation drawer
│   │   └── TopNav.tsx                 # Breadcrumbs, date picker, alerts, and profile
│   ├── tables/
│   │   ├── BranchPerformanceTable.tsx # Regional sales target fulfillment table
│   │   ├── DqChecksTable.tsx          # Granular assertion log with dataset filter
│   │   ├── ExpensesTable.tsx          # Branch OpEx ledger with variance calculation
│   │   ├── InventoryTable.tsx         # SKU health table with status & warehouse filters
│   │   ├── PurchaseOrdersTable.tsx    # PO tracking table with status & date sorting
│   │   ├── SalesTransactionsTable.tsx # Searchable sales transaction log
│   │   ├── SuppliersTable.tsx         # Vendor scorecard table with risk tier filters
│   │   ├── TaskMetricsTable.tsx       # Airflow task duration & variance table
│   │   └── TopProductsTable.tsx       # High-velocity SKU ranking table
│   └── ui/
│       ├── DateRangePicker.tsx        # Dropdown date range selector
│       ├── EmptyState.tsx             # Standard empty, loading, and error states
│       ├── KpiCard.tsx                # Metric card with icons, trends, and captions
│       ├── SearchFilter.tsx           # Reusable search input with clear trigger
│       └── StatusBadge.tsx            # Standardized pill badges with semantic dots
├── lib/
│   ├── api/
│   │   └── client.ts                  # Abstracted API client & response contracts
│   ├── mock-data/
│   │   ├── dataQualityData.ts         # Day 7 mirror (210 checks, 12 Silver datasets)
│   │   ├── expensesData.ts            # OpEx budgets, categories, and branch costs
│   │   ├── inventoryData.ts           # 4 warehouse sites, SKU safety thresholds
│   │   ├── monitoringData.ts          # Day 8 mirror (30 tasks, run telemetry, lineage)
│   │   ├── notifications.ts           # Alert center events and status feeds
│   │   ├── overviewData.ts            # Executive KPIs, velocity curves, and activities
│   │   ├── procurementData.ts         # Purchase orders, receipts, lead times
│   │   ├── salesData.ts               # Transactions, channels, and margin metrics
│   │   └── suppliersData.ts           # Tier-1 vendor directory and ratings
│   └── utils.ts                       # Currency, number, date formatters & cn()
├── types/
│   └── index.ts                       # Complete domain entity type definitions
├── tailwind.config.ts                 # Extended enterprise palette & typography
├── tsconfig.json                      # Strict TypeScript compiler options
└── package.json                       # Next.js 14, React 18, Recharts, Lucide React
```

---

## 3. Implemented Routes & Capabilities

| Route | Title | Key Metrics & Components |
| :--- | :--- | :--- |
| `/` | **Executive Overview** | Total Revenue ($1.84M), Gross Profit ($589k), Orders (20k), Inventory Value ($3.41M), Stockout Rate (1.8%), Open POs (42). Revenue Velocity Chart, Channel Share Donut, Top Products, Branch Performance, Live Airflow Pipeline Status Widget, Activity Feed. |
| `/sales` | **Sales Analytics** | Gross Sales, Net Sales ($1.84M), Average Order Value ($92.15), Discounts, Return Rate (1.2%), Active Customers (8,420). Sales Velocity Area Chart, Category Margin Breakdown, Sortable & Filterable Transactions Table. |
| `/inventory` | **Inventory & Fulfillment** | Stock Value ($3.41M), Active SKUs (2,480), Turnover Ratio (6.4x), Low Stock (28 SKUs), Stockouts (4 SKUs), Facility Utilization (78.4%). 4 Warehouse Facility Capacity Cards, Interactive Inventory Table with Status & Warehouse multi-filters. |
| `/procurement` | **Procurement Analytics** | Committed PO Spend ($485k), Avg Lead Time (8.4 Days), On-Time Delivery (94.2%), Goods Receipts (1,453), PO Match Rate (99.1%). PO Status Breakdown distribution cards, Purchase Orders Registry with search & sorting. |
| `/suppliers` | **Supplier Performance** | Active Tier-1 Suppliers (64), Avg Fulfillment (97.4%), Rating Score (4.7/5.0), YTD Spend ($4.12M), High Risk Vendors (2). Supplier Scorecard Directory with Risk Tier filtering and spend sorting. |
| `/expenses` | **Operating Expenses** | Total OpEx ($384k), OpEx to Revenue Ratio (20.8%), Budget Variance (-$10.3k favorable), Freight ($114k), Rent ($142k), Utilities. Monthly Budget vs. Actual Bar Chart, Category Share breakdown, Sortable OpEx Ledger Table. |
| `/monitoring` | **Pipeline Observability** | Execution Status (`SUCCESS`), Duration (28.32s), Tasks Succeeded (30/30), Failures (0), Total Medallion Records (150,627). Medallion Volume Lineage Chart (Raw -> Bronze -> Silver -> Gold), Task Execution Breakdown with duration variance against historical averages. |
| `/data-quality` | **Data Quality Framework** | Quality Score (100.0%), Checks Executed (210), Passed (210), Failed (0), Silver Datasets (12/12), Promotion Status (`PROMOTED`). Rule Category Pass Distribution (5 domains), 12 Silver Datasets Audit Matrix, Granular Assertion Log Table. |
| `/settings` | **Platform Settings** | Configurable dashboard polling cadence, automated alert routing (pipeline failures, DQ violations, stockout breaches), and system runtime diagnostics (Airflow 3.4.0, PostgreSQL DW, Next.js 14). |

---

## 4. Design System & Visual Specification

- **Sidebar Background**: Deep Navy (`#0F172A` / `#0B1120`) with subtle border separator (`#1E293B`).
- **Workspace Background**: Crisp slate neutral (`#F8FAFC`).
- **Card Panels**: Pure white (`#FFFFFF`) with subtle border (`border-slate-200/80`) and elevated soft shadow (`shadow-sm`).
- **Brand Accents**:
  - Primary / Interactive: `#2563EB` (Blue 600)
  - Success / Financial Gains / Pass: `#10B981` (Emerald 500)
  - Warning / Low Stock / Pending: `#F59E0B` (Amber 500)
  - Critical / Stockout / Failure: `#EF4444` (Rose 500)
  - Channels / Tech: `#06B6D4` (Cyan 500) & `#8B5CF6` (Violet 500)
- **Typography**: Clean system font stack (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`) with tight letter-spacing for numerals and uppercase tracker labels.

---

## 5. Verification & Build Results

All automated checks were executed in the `frontend/` directory with clean results:

### 1. TypeScript Strict Type-Checking
```powershell
npm.cmd run type-check
```
- **Command**: `tsc --noEmit`
- **Result**: `Exit code 0` — 0 errors across all routes, components, and mock modules.

### 2. ESLint Code Quality
```powershell
npm.cmd run lint
```
- **Command**: `next lint`
- **Result**: `✔ No ESLint warnings or errors` (Exit code 0).

### 3. Production Static Page Generation & Build
```powershell
npm.cmd run build
```
- **Command**: `next build`
- **Outcome**:
  ```text
  ✓ Compiled successfully
    Linting and checking validity of types ...
    Collecting page data ...
  ✓ Generating static pages (12/12)
    Finalizing page optimization ...

  Route (app)                              Size     First Load JS
  ┌ ○ /                                    10.7 kB         227 kB
  ├ ○ /_not-found                          876 B          88.4 kB
  ├ ○ /data-quality                        4.36 kB         102 kB
  ├ ○ /expenses                            5.24 kB         205 kB
  ├ ○ /inventory                           5.79 kB         104 kB
  ├ ○ /monitoring                          5.76 kB         205 kB
  ├ ○ /procurement                         5.09 kB         103 kB
  ├ ○ /sales                               4 kB            212 kB
  ├ ○ /settings                            2.8 kB         90.3 kB
  └ ○ /suppliers                           4.88 kB         103 kB
  + First Load JS shared by all            87.5 kB
  ```
- **Pages Compiled**: 12 static optimized pages generated without warnings.

---

## 6. How to Run the Frontend

To start the OpsPulse frontend in local development or production mode:

### Development Mode (with hot-reload)
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"
npm.cmd run dev
```
Access the application at [http://localhost:3000](http://localhost:3000).

### Production Build & Serve
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"
npm.cmd run build
npm.cmd run start
```
Access the production server at [http://localhost:3000](http://localhost:3000).
