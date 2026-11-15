"""
OpsPulse Vercel Serverless Function Entry Point for FastAPI Backend.

Exposes the ASGI `app` instance for Vercel's Python Serverless Runtime.
Dynamically resolves `backend/src` on sys.path so existing modular architecture
and relative imports remain untouched.
"""

import sys
from pathlib import Path

# Add backend/src to Python module search path
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Import the existing production FastAPI ASGI app
from api.main import app

# Export app for Vercel runtime
__all__ = ["app"]
