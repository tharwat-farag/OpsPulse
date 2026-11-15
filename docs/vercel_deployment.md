# OpsPulse — Vercel & Neon Cloud Deployment Guide

This guide provides the complete, step-by-step instructions for deploying the **OpsPulse Retail & Distribution Intelligence Platform** to the cloud using:

- **Vercel** for the Next.js 14 Frontend.
- **Vercel** for the FastAPI Analytical Backend (Serverless Functions).
- **Neon PostgreSQL** for the Cloud Data Warehouse.

> **Zero Third-Party VM Dependencies:** Render is **not** required. The entire application runs serverlessly on Vercel and Neon with zero ongoing infrastructure costs when idle.

---

## Architecture Overview

Both the frontend and backend are deployed from the **same single GitHub repository** (`tharwat-farag/OpsPulse`) as two independent Vercel projects:

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
│  - Framework: Next.js 14 App Router   │ │  - Runtime: Python Serverless │
│  - UI: Tailwind CSS, Recharts, Lucide │ │  - Framework: FastAPI ASGI    │
│  - Proxy: rewrites /api/* to Backend  │ │  - Entry: backend/api/index.py│
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

---

## Prerequisites

1. **GitHub Account:** Access to the published repository [https://github.com/tharwat-farag/OpsPulse](https://github.com/tharwat-farag/OpsPulse).
2. **Vercel Account:** Free Hobby or Pro tier at [vercel.com](https://vercel.com).
3. **Neon Account:** Free Serverless PostgreSQL tier at [neon.tech](https://neon.tech).
4. **Local OpsPulse Warehouse:** Your populated local PostgreSQL warehouse `opspulse_dw` (for initial one-time replication).

---

## Step 1: Provision Neon PostgreSQL & Replicate Data

### 1.1 Create a Neon Database Project
1. Log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**.
3. Name the project `opspulse-dw`.
4. Choose your preferred region (e.g. `aws-us-east-2`).
5. Neon will provide your connection string:
   ```text
   postgresql://neondb_owner:AbCd1234_xyz@ep-cool-butterfly-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### 1.2 Replicate Warehouse to Neon
OpsPulse includes an idempotent, non-destructive replication utility that safely migrates schemas, tables, surrogate keys, and identity columns without dropping tables:

```bash
# In the OpsPulse project root:
.venv\Scripts\python scripts/replicate_warehouse_to_cloud.py \
  --target "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  --mode safe
```

> **Identity Column Handling:** The replication engine automatically uses `OVERRIDING SYSTEM VALUE` for `GENERATED ALWAYS AS IDENTITY` columns, inserts via `ON CONFLICT DO NOTHING`, and synchronizes all sequence counters with `pg_get_serial_sequence()`.

### 1.3 Verify Target Data
The script performs automatic business verification at the end. Confirm the target warehouse matches the ground-truth metrics:
- **Net Revenue:** `$357,426,869.05`
- **Gross Sales Amount:** `$380,108,747.31`
- **Invoices:** `8,053`
- **Inventory Value:** `$17,169,853.11`
- **Active Suppliers:** `10`
- **Date Dimension:** `730` rows (2024-01-01 through 2025-12-31)

---

## Step 2: Deploy Project A — FastAPI Backend on Vercel

### 2.1 Create Project in Vercel
1. In the Vercel Dashboard, click **Add New...** → **Project**.
2. Select your GitHub repository: `tharwat-farag/OpsPulse`.
3. In **Project Name**, enter: `opspulse-api` (or your preferred name).
4. Under **Framework Preset**, select **Other**.
5. Under **Root Directory**, click **Edit** and select:
   ```text
   backend
   ```
6. Leave **Build Command** and **Output Directory** at default.

### 2.2 Configure Backend Environment Variables
In the **Environment Variables** section, add:

| Name | Value | Description |
| :--- | :--- | :--- |
| `OPSPULSE_DATABASE_URL` | `postgresql+psycopg://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require` | Neon connection string with SSL |
| `OPSPULSE_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Local dev origins (update after frontend deploy) |

> **Note on Connection Pooling:** When running on Vercel (`VERCEL=1`), `backend/src/warehouse/db_connection.py` automatically initializes SQLAlchemy with `NullPool`. This prevents connection pool exhaustion on Neon across serverless function invocations.

### 2.3 Deploy & Verify Backend
1. Click **Deploy**.
2. Once deployed, note your backend domain (e.g. `https://opspulse-api.vercel.app`).
3. Test the endpoints in your browser:
   - Root: `https://opspulse-api.vercel.app/` → `{"service":"OpsPulse Analytics API","status":"online",...}`
   - Health: `https://opspulse-api.vercel.app/api/health` → `{"status":"healthy","database":"connected",...}`
   - Overview: `https://opspulse-api.vercel.app/api/overview` → Returns JSON executive metrics
   - Interactive Docs: `https://opspulse-api.vercel.app/docs` → Swagger UI

---

## Step 3: Deploy Project B — Next.js Frontend on Vercel

### 3.1 Create Project in Vercel
1. In the Vercel Dashboard, click **Add New...** → **Project**.
2. Select the same GitHub repository: `tharwat-farag/OpsPulse`.
3. In **Project Name**, enter: `opspulse-web` (or `opspulse-dashboard`).
4. Under **Framework Preset**, ensure **Next.js** is selected.
5. Under **Root Directory**, click **Edit** and select:
   ```text
   frontend
   ```

### 3.2 Configure Frontend Environment Variables
In the **Environment Variables** section, add:

| Name | Value | Description |
| :--- | :--- | :--- |
| `BACKEND_API_URL` | `https://opspulse-api.vercel.app/api` | Your deployed Project A backend URL |
| `NEXT_PUBLIC_API_URL` | `/api` | Relative API path (proxied server-side by Next.js) |

### 3.3 Deploy & Verify Frontend
1. Click **Deploy**.
2. Once the build completes, visit your live dashboard URL (e.g. `https://opspulse-web.vercel.app`).
3. Verify that all 9 pages load and display live PostgreSQL metrics:
   - `/` (Executive Overview)
   - `/sales` (Sales Performance & Channel Analytics)
   - `/inventory` (Warehouse Stock & Reorder Alerts)
   - `/procurement` (Purchase Orders & Fulfillment)
   - `/suppliers` (Supplier Performance Scorecards)
   - `/expenses` (Operating Expenses Breakdown)
   - `/monitoring` (Airflow Pipeline Execution Telemetry)
   - `/data-quality` (Automated Data Quality Audit Suite)
   - `/settings` (System Configuration & Connection Status)

---

## Step 4: Security Hardening (CORS Lockdown)

Now that you have your production frontend URL (e.g. `https://opspulse-web.vercel.app`):

1. Open your Vercel **Backend Project** (`opspulse-api`).
2. Navigate to **Settings** → **Environment Variables**.
3. Edit `OPSPULSE_ALLOWED_ORIGINS`:
   ```text
   https://opspulse-web.vercel.app,http://localhost:3000
   ```
4. Click **Save** and trigger a **Redeploy** on the backend project.

> Because Next.js rewrites proxy requests server-to-server from `/api/*` to `BACKEND_API_URL`, the browser communicates exclusively with same-origin `opspulse-web.vercel.app`, avoiding all CORS and third-party cookie restrictions.

---

## Step 5: Summary of Files & Architecture Components

| File | Purpose |
| :--- | :--- |
| `backend/api/index.py` | Vercel Serverless Function entry point exporting FastAPI `app`. |
| `backend/vercel.json` | URL rewrite rule routing `/(.*)` to `/api/index.py`. |
| `backend/requirements.txt` | Lean production dependencies for Python serverless runtime. |
| `backend/src/warehouse/db_connection.py` | Automatically detects `VERCEL=1` and uses `NullPool` for safe database access. |
| `frontend/next.config.mjs` | Configures server-side reverse proxy from `/api/:path*` to `BACKEND_API_URL`. |
| `frontend/lib/api/client.ts` | Default client baseUrl defaults to `/api`, adapting to both local dev and production. |
| `scripts/replicate_warehouse_to_cloud.py` | Automated, idempotent migration script with `OVERRIDING SYSTEM VALUE` support. |

---

## Troubleshooting

### 1. Backend Returns 503 "database": "disconnected"
- **Cause:** Neon connection string missing or SSL parameter omitted.
- **Remedy:** Ensure `OPSPULSE_DATABASE_URL` contains `?sslmode=require` and valid credentials.
- Test connection via psql or Python locally before deploying.

### 2. Frontend Shows "Cannot reach backend API"
- **Cause:** `BACKEND_API_URL` in the frontend project is either unset or pointing to `localhost`.
- **Remedy:** In `opspulse-web` Settings → Environment Variables, set `BACKEND_API_URL` to `https://<your-opspulse-api>.vercel.app/api`. Redeploy the frontend.

### 3. PostgreSQL Identity Column Errors on Replication
- If replicating manually without the script, PostgreSQL will block inserts into `GENERATED ALWAYS AS IDENTITY` columns.
- **Remedy:** Always run `python scripts/replicate_warehouse_to_cloud.py --mode safe`, which handles `OVERRIDING SYSTEM VALUE` and sequence resetting automatically.
