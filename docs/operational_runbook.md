# OpsPulse — Operational Runbook & Production Administration Guide

This runbook is the definitive operational reference for administrators, DevOps engineers, and developers managing the **OpsPulse Retail & Distribution Business Operations Intelligence Platform** on Windows environments.

---

## 1. System Architecture & Topology

OpsPulse operates as a 3-tier enterprise analytical platform:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Web Browser (Client Tier)                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   │ HTTP :3000 (Same-Origin & SSR)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Presentation Tier: Next.js 14.2.35 (Port 3000)                        │
│  • App Router (9 Routes: /, /sales, /inventory, /procurement, etc.)    │
│  • Reverse-Proxy Rewrites (/api/* -> http://127.0.0.1:8000/api/*)      │
│  • Global DateRangeContext & Persistent User Settings (localStorage)   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   │ HTTP :8000 (Internal JSON REST API)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Application Tier: Python FastAPI (Port 8000 / Uvicorn)                 │
│  • 12 Analytical Domain Endpoints with Parameterized SQL               │
│  • CORS Whitelist Middleware for Local Ports 3000 & 3001                │
│  • Automatic Root .env Ingestion & Connection Pooling                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   │ TCP :5432 (psycopg / SQLAlchemy 2.0)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Data & Analytics Tier: PostgreSQL 16+ (Port 5432)                      │
│  • Database: opspulse_dw                                               │
│  • Schemas: staging, silver, gold, monitoring                          │
│  • Airflow 3.4.0 Batch Pipeline (DAG: opspulse_pipeline)               │
└────────────────────────────────────────────────────────────────────────┘
```

### Port Allocations

| Service | Protocol | Default Host / Port | Purpose |
| :--- | :--- | :--- | :--- |
| **Next.js Frontend** | HTTP | `http://localhost:3000` | Enterprise analytics dashboard UI |
| **FastAPI Backend** | HTTP | `http://127.0.0.1:8000` | REST API analytical service |
| **PostgreSQL Database** | TCP | `localhost:5432` | Data warehouse (`opspulse_dw`) |
| **Airflow Webserver** | HTTP | `http://localhost:8080` | Airflow 3.4.0 orchestration GUI |

---

## 2. Prerequisites & Environment Configuration

### System Prerequisites
- **Operating System:** Windows 10/11 (or Windows Server 2019/2022)
- **Node.js:** v20.10.0+ / npm v10.0.0+
- **Python:** v3.11+ or v3.13+ 64-bit
- **PostgreSQL:** PostgreSQL 16+ installed locally or accessible over LAN
- **PowerShell:** PowerShell 5.1 or PowerShell 7+

### Environment Configuration Files

#### 1. Root `.env` (`D:\Data Engineer Projects\OpsPulse\.env`)
Used by backend Python scripts, warehouse connection pool, and analytical API:
```ini
OPSPULSE_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/opspulse_dw
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### 2. Frontend Configuration (`frontend/.env.local`)
Used by Next.js client-side code and server-side reverse proxy:
```ini
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```
> [!IMPORTANT]
> Always use IPv4 `127.0.0.1` rather than `localhost` in `NEXT_PUBLIC_API_URL` to avoid Windows dual-stack IPv6 (`::1`) loopback connection drops.

---

## 3. Standard Operational Startup Procedures

### Method A: Automated One-Click Launcher (Recommended)

OpsPulse includes an automated launcher script that tests database connectivity, kills lingering port locks, and starts both backend and frontend in dedicated console windows:

```powershell
# Open PowerShell in project root
cd "D:\Data Engineer Projects\OpsPulse"
.\start_opspulse.ps1
```

The launcher executes the following sequence:
1. Validates Python virtual environment at `.venv`.
2. Tests direct PostgreSQL connection and query execution.
3. Automatically frees any stale processes on ports 3000 and 8000.
4. Spawns FastAPI backend (`uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload`).
5. Spawns Next.js production server (`npm.cmd start` on port 3000).

---

### Method B: Manual Step-by-Step Launch

#### Step 1: Verify / Start PostgreSQL
Check whether the PostgreSQL Windows service is running:
```powershell
Get-Service -Name postgresql*
```
If stopped, start the service:
```powershell
Start-Service -Name "postgresql-x64-16"
# Alternatively via net:
net start postgresql-x64-16
```

#### Step 2: Start the FastAPI Backend
Open **Terminal 1**:
```powershell
cd "D:\Data Engineer Projects\OpsPulse"
$env:PYTHONPATH = "backend/src"
.venv\Scripts\uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Expected Output:*
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

#### Step 3: Start the Next.js Frontend
Open **Terminal 2**:
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"

# Production Mode (Optimized):
npm.cmd run build
npm.cmd start

# OR Development Mode (Hot Reload):
npm.cmd run dev
```
*Expected Output:*
```text
   ▲ Next.js 14.2.35
   - Local:        http://localhost:3000
   - Network:      http://127.0.0.1:3000

 ✓ Ready in 450ms
```

---

## 4. Verification & Health Probes

### 1. Backend API Health Check
Run in PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" | ConvertTo-Json
```
*Expected Response:*
```json
{
  "status": "healthy",
  "database": "connected",
  "service": "opspulse-api"
}
```

### 2. Next.js Reverse-Proxy Health Check
Verify that Next.js successfully proxies requests to the backend:
```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/health" | ConvertTo-Json
```
*Expected Response:* Same `healthy` payload as direct backend.

### 3. Core Data API Endpoint Probes
```powershell
# Executive Overview
Invoke-RestMethod -Uri "http://localhost:3000/api/overview?year=2025"

# Sales Summary & Transactions
Invoke-RestMethod -Uri "http://localhost:3000/api/sales?year=2025"

# Inventory Valuation
Invoke-RestMethod -Uri "http://localhost:3000/api/inventory"

# Procurement & PO Tracking
Invoke-RestMethod -Uri "http://localhost:3000/api/procurement"

# Operating Expenses
Invoke-RestMethod -Uri "http://localhost:3000/api/expenses?year=2025"

# Observability Telemetry
Invoke-RestMethod -Uri "http://localhost:3000/api/monitoring"

# Data Quality Report
Invoke-RestMethod -Uri "http://localhost:3000/api/data-quality"
```

### 4. Frontend Route HTTP Status Check
```powershell
$routes = @("/", "/sales", "/inventory", "/procurement", "/suppliers", "/expenses", "/monitoring", "/data-quality", "/settings")
foreach ($r in $routes) {
    $res = Invoke-WebRequest -Uri "http://localhost:3000$r" -UseBasicParsing
    Write-Host "$r -> Status $($res.StatusCode)"
}
```
*Expected Output:* All 9 routes return HTTP 200.

---

## 5. Graceful Shutdown & Port Management

### Clean Process Termination
- In the FastAPI terminal: Press `Ctrl + C`.
- In the Next.js terminal: Press `Ctrl + C`.

### Clearing Stale Port Locks (Troubleshooting Port Conflicts)
If a process crashes or continues running in the background, ports 3000 or 8000 may become locked:

```powershell
# 1. Identify process occupying port 3000
$port3000Pid = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($port3000Pid) {
    Write-Host "Terminating process on port 3000 (PID: $port3000Pid)"
    Stop-Process -Id $port3000Pid -Force
}

# 2. Identify process occupying port 8000
$port8000Pid = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($port8000Pid) {
    Write-Host "Terminating process on port 8000 (PID: $port8000Pid)"
    Stop-Process -Id $port8000Pid -Force
}

# 3. Terminate any orphaned node or uvicorn processes
Get-Process -Name node, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 6. Testing & Quality Assurance Procedures

### 1. Backend Automated Pytest Suite
Run the full 121-test suite:
```powershell
cd "D:\Data Engineer Projects\OpsPulse"
.venv\Scripts\pytest
```
*Expected Result:* `121 passed, 1 warning in ~6.5s` (Exit code 0).

### 2. Frontend Type Checking
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"
npm.cmd run type-check
```
*Expected Result:* 0 errors (Exit code 0).

### 3. Frontend Linting
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"
npm.cmd run lint
```
*Expected Result:* `✔ No ESLint warnings or errors` (Exit code 0).

### 4. Production Build Verification
```powershell
cd "D:\Data Engineer Projects\OpsPulse\frontend"
npm.cmd run build
```
*Expected Result:* `Compiled successfully (12/12 static pages)` (Exit code 0).

### 5. Data Quality Suite Execution
To execute the automated data quality checks against the Silver layer:
```powershell
cd "D:\Data Engineer Projects\OpsPulse"
$env:PYTHONPATH = "backend/src"
.venv\Scripts\python backend/src/validation/data_quality/run_quality_checks.py
```
*Expected Result:* 210 assertions evaluated, 100% pass rate.

---

## 7. Troubleshooting & Operational Runbook Scenarios

### Scenario 1: `Live Data Service Offline: Failed to fetch`
- **Symptom:** Red offline banner displayed in top navigation bar; cards display empty state.
- **Root Cause Analysis:**
  1. FastAPI backend is not running or crashed.
  2. Browser fetch failed due to IPv6 localhost resolution mismatch (`[::1]` instead of `127.0.0.1`).
- **Remediation Steps:**
  1. Test backend directly: `curl http://127.0.0.1:8000/api/health`.
  2. If backend is down, start it using Step 2 of Manual Launch.
  3. Ensure `frontend/.env.local` contains `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api`.
  4. Ensure `frontend/next.config.mjs` has the reverse proxy rewrite enabled.

---

### Scenario 2: `ChunkLoadError: Loading chunk ... failed`
- **Symptom:** Browser console logs `ChunkLoadError` when clicking sidebar routes.
- **Root Cause Analysis:**
  Running `npm run dev` and `npm start` concurrently. The dev server deletes and regenerates chunk files in `.next/static/chunks/` with new hashes while the start server serves the old HTML manifest.
- **Remediation Steps:**
  1. Kill all Node processes: `Get-Process -Name node | Stop-Process -Force`.
  2. Delete stale build cache: `Remove-Item -Recurse -Force "frontend\.next"`.
  3. Rebuild cleanly: `cd frontend; npm.cmd run build`.
  4. Start only ONE mode: either `npm run dev` OR `npm start`.

---

### Scenario 3: Database Connection Refused / `OPSPULSE_DATABASE_URL not set`
- **Symptom:** Backend logs `ValueError: OPSPULSE_DATABASE_URL environment variable is not set` or `psycopg.OperationalError: connection to server at "localhost" failed`.
- **Root Cause Analysis:**
  - `.env` file missing from project root, or PostgreSQL service is stopped.
- **Remediation Steps:**
  1. Ensure `.env` exists in `D:\Data Engineer Projects\OpsPulse\.env` with valid connection string.
  2. Verify PostgreSQL service status: `Get-Service -Name postgresql*`.
  3. Test connection directly using Python:
     ```powershell
     .venv\Scripts\python -c "from warehouse.db_connection import get_database_engine; print(get_database_engine().connect())"
     ```

---

### Scenario 4: Port Conflict (`EADDRINUSE: 3000` or `WinError 10048`)
- **Symptom:** Uvicorn or Next.js crashes on startup stating the port is already bound.
- **Remediation Steps:**
  Execute the automated port clearing script detailed in **Section 5: Clearing Stale Port Locks**.

---

### Scenario 5: Date Range Filter Dynamics
- **Operational Rule:**
  The OpsPulse historical transaction data warehouse represents Calendar Year 2025 (`2025-01-01` to `2025-12-31`).
- **Date Selector Options:**
  - `FY 2025 (Full Year)`: Queries `d.year_number = 2025` ($357.43M net revenue, 8,053 invoices).
  - `Q1 2025`: Queries `d.year_number = 2025 AND d.quarter_number = 1` ($87.27M).
  - `Q2 2025`: Queries `d.year_number = 2025 AND d.quarter_number = 2` ($90.20M).
  - `Q3 2025`: Queries `d.year_number = 2025 AND d.quarter_number = 3` ($91.16M).
  - `Q4 2025`: Queries `d.year_number = 2025 AND d.quarter_number = 4` ($88.81M).
  - `All Available Data`: Queries without year restriction.
- **Global Context:** Date range choice persists across page navigation and is stored in browser `localStorage` (`opspulse_date_range`).

---

### Scenario 6: Auto-Refresh & Background Polling
- **Configuration:** Accessible in `/settings`.
- **Options:** `Off`, `30 Seconds`, `1 Minute`, `5 Minutes`.
- **Persistence:** Saved in `localStorage` under key `opspulse_refresh_interval`.
- **Behavior:** When enabled, an active background polling timer triggers data reload across active dashboard components without full page reloads.

---

## 8. Operational Sign-Off Verification Checklist

Prior to production sign-off or executive demonstration, verify each item:

- [x] **PostgreSQL Service:** `opspulse_dw` running and accepting connections on port 5432.
- [x] **FastAPI Backend:** Uvicorn running on `127.0.0.1:8000`, `/api/health` returns `healthy`.
- [x] **Next.js Frontend:** Port 3000 compiled without errors, reverse proxy functional.
- [x] **9 Routes Verified:** All 9 dashboard routes return HTTP 200 with live warehouse data.
- [x] **Reconciliation:** Sales, inventory, procurement, and expenses match warehouse ground truth.
- [x] **Automated Tests:** 121 backend pytest tests passing; TypeScript and ESLint report 0 errors.
- [x] **Security:** No secrets or credentials committed to git or exposed to browser client bundles.
- [x] **Operational Launcher:** `start_opspulse.ps1` operational and verified.
