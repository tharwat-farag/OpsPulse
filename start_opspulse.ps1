# OpsPulse — Interactive Application Launcher
# Starts FastAPI backend (port 8000) and Next.js frontend (port 3000)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       OpsPulse Enterprise Data Platform Launcher         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Environment and Path Check
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
Write-Host "[1/4] Project Root: $projectRoot" -ForegroundColor Gray

# 2. Verify Python Virtual Environment
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found at .venv. Please create it first." -ForegroundColor Red
    Exit 1
}

# 3. Test PostgreSQL Connectivity
Write-Host "[2/4] Testing PostgreSQL opspulse_dw database connectivity..." -ForegroundColor Yellow
$env:PYTHONPATH = "backend/src"
$dbTest = & $venvPython -c "
from warehouse.db_connection import get_database_engine
from sqlalchemy import text
try:
    engine = get_database_engine()
    with engine.connect() as conn:
        res = conn.execute(text('SELECT 1')).scalar()
        print('CONNECTED' if res == 1 else 'FAILED')
except Exception as e:
    print('ERROR:', e)
"

if ($dbTest -ne "CONNECTED") {
    Write-Host "[WARNING] Database test returned: $dbTest" -ForegroundColor Yellow
    Write-Host "Ensure PostgreSQL is running on localhost:5432 and database opspulse_dw exists." -ForegroundColor Yellow
} else {
    Write-Host "[SUCCESS] PostgreSQL connection verified." -ForegroundColor Green
}

# 4. Stop any stale Node or Uvicorn instances on ports 3000 / 8000
Write-Host "[3/4] Checking for lingering processes on ports 3000 & 8000..." -ForegroundColor Gray
$stale3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
$stale8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($stale3000) { Stop-Process -Id $stale3000 -Force -ErrorAction SilentlyContinue }
if ($stale8000) { Stop-Process -Id $stale8000 -Force -ErrorAction SilentlyContinue }

# 5. Launch FastAPI Backend in a new terminal window
Write-Host "[4/4] Starting FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; `$env:PYTHONPATH='backend/src'; .venv\Scripts\uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

# Wait briefly for FastAPI to initialize
Start-Sleep -Seconds 2

# 6. Launch Next.js Frontend in a new terminal window
Write-Host "[4/4] Starting Next.js frontend on http://localhost:3000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\frontend'; npm.cmd start"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "OpsPulse platform started successfully!" -ForegroundColor Green
Write-Host " - Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host " - Backend:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host " - API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " - Health:    http://127.0.0.1:8000/api/health" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
