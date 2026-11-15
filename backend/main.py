"""
OpsPulse Backend API - Vercel FastAPI Production Entry Point.

Exposes the ASGI `app` instance for Vercel's Zero-Configuration FastAPI Framework Preset.
Dynamically injects `backend/src` onto sys.path to resolve all application routes,
warehouse connections, and business logic without code duplication.
"""

import sys
from pathlib import Path

# Add backend/src to Python module search path
_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Import and expose the production FastAPI ASGI application
from api.main import app

__all__ = ["app"]
