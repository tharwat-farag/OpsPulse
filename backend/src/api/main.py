"""
OpsPulse Backend API - FastAPI Application Entry Point.

Serves analytical and operational endpoints from PostgreSQL opspulse_dw.
Enforces strict CORS for local frontend development and parameterized SQL queries.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.database import check_db_health, get_engine
from api.routes import (
    overview,
    sales,
    inventory,
    procurement,
    suppliers,
    expenses,
    monitoring,
    data_quality,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and verifies database connectivity on startup."""
    print("[OpsPulse API] Starting up... Verifying PostgreSQL connection.")
    db_ok = check_db_health()
    if db_ok:
        print("[OpsPulse API] PostgreSQL opspulse_dw connection verified successfully.")
    else:
        print("[OpsPulse API] Warning: Could not verify PostgreSQL connection on startup.")
    yield
    print("[OpsPulse API] Shutting down.")


app = FastAPI(
    title="OpsPulse Live Analytics API",
    description="Operational and analytical API serving OpsPulse Retail & Distribution intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# Restricts access to local Next.js frontend origin
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# Allow additional origins if defined in environment
custom_cors = os.getenv("OPSPULSE_ALLOWED_ORIGINS")
if custom_cors:
    ALLOWED_ORIGINS.extend([orig.strip() for orig in custom_cors.split(",") if orig.strip()])

# Standard CORS compliance: cannot use allow_credentials=True with wildcard origin
allow_credentials = "*" not in ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to return clean JSON errors without leaking stack traces."""
    print(f"[OpsPulse API] Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An error occurred while processing the operational query.",
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/api/health", tags=["Health"])
def health_check():
    """
    Health check endpoint reporting API status and PostgreSQL connectivity.
    """
    db_healthy = check_db_health()
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
            "service": "opspulse-api",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Include API Routers under /api
app.include_router(overview.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(procurement.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(data_quality.router, prefix="/api")
