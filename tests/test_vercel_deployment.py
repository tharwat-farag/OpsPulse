"""
Tests for OpsPulse Vercel Deployment configuration and entry points.
"""

import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool

from warehouse.db_connection import get_database_engine
from backend.api.index import app


def test_vercel_entrypoint_app():
    """Verify that backend/api/index.py exports a valid FastAPI ASGI app."""
    assert isinstance(app, FastAPI)
    assert app.title == "OpsPulse Live Analytics API"


def test_vercel_root_endpoint():
    """Verify that GET / returns 200 with metadata."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "OpsPulse Analytics API"
    assert data["status"] == "online"
    assert "/api/health" in data["health"]
    assert "/docs" in data["docs"]


def test_serverless_nullpool_engine(monkeypatch):
    """Verify that VERCEL=1 causes get_database_engine to configure NullPool."""
    monkeypatch.setenv("VERCEL", "1")
    engine = get_database_engine()
    assert isinstance(engine.pool, NullPool)
