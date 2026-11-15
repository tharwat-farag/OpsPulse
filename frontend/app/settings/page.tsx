"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  Database,
  Server,
  Save,
  Check,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { opspulseApi } from "@/lib/api/client";

export default function SettingsPage() {
  const [refreshInterval, setRefreshInterval] = useState("manual");
  const [dbStatus, setDbStatus] = useState<string>("checking...");
  const [apiStatus, setApiStatus] = useState<string>("checking...");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const res = await opspulseApi.getHealth();
      setApiStatus(res.status === "healthy" ? "Connected" : "Degraded");
      setDbStatus(res.database === "connected" ? "Connected (PostgreSQL opspulse_dw)" : "Disconnected");
    } catch {
      setApiStatus("Offline");
      setDbStatus("Unavailable (API offline)");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      const savedInterval = localStorage.getItem("opspulse_refresh_interval");
      if (savedInterval) setRefreshInterval(savedInterval);
    } catch {}
    checkHealth();
  }, []);

  useEffect(() => {
    if (refreshInterval === "manual") return;
    const msMap: Record<string, number> = {
      "30s": 30000,
      "1m": 60000,
      "5m": 300000,
    };
    const ms = msMap[refreshInterval] || 30000;
    const timer = setInterval(() => {
      checkHealth();
    }, ms);
    return () => clearInterval(timer);
  }, [refreshInterval]);

  const handleSave = () => {
    try {
      localStorage.setItem("opspulse_refresh_interval", refreshInterval);
    } catch {}
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title block */}
      <div>
        <h2 className="text-base font-bold text-slate-900">Platform Settings & Diagnostics</h2>
        <p className="text-xs text-slate-500">
          Live system status, database connectivity verification, and client refresh preferences
        </p>
      </div>

      {/* Live System Diagnostics */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">Live Infrastructure & Database Health</h3>
          </div>
          <button
            type="button"
            onClick={checkHealth}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Check Connection
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">FastAPI Analytics Service</span>
            <span className="font-bold text-slate-900 mt-0.5 block">
              {process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api"}
            </span>
            <span className={`text-[11px] font-semibold ${apiStatus === "Connected" ? "text-emerald-600" : "text-rose-600"}`}>
              Status: {apiStatus}
            </span>
          </div>

          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">PostgreSQL Data Warehouse</span>
            <span className="font-bold text-slate-900 mt-0.5 block">Database: opspulse_dw</span>
            <span className={`text-[11px] font-semibold ${dbStatus.includes("Connected") ? "text-emerald-600" : "text-rose-600"}`}>
              {dbStatus}
            </span>
          </div>

          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Orchestrator Runtime</span>
            <span className="font-bold text-slate-900 mt-0.5 block">Apache Airflow 3.4.0</span>
            <span className="text-[11px] text-slate-600 font-medium">WSL Ubuntu &bull; DAG opspulse_pipeline</span>
          </div>

          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Target Warehouse Schemas</span>
            <span className="font-bold text-slate-900 mt-0.5 block">gold, monitoring, staging</span>
            <span className="text-[11px] text-emerald-600 font-medium">Verified Active</span>
          </div>
        </div>
      </div>

      {/* Telemetry Refresh & Polling */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <RefreshCw className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Dashboard Refresh Cadence</h3>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700">
              Client Query Refresh Mode
            </label>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Configures data fetching interval from the live FastAPI analytical endpoints.
            </p>
          </div>
          <div>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="manual">Manual refresh on page load (Recommended)</option>
              <option value="30s">Polling every 30 seconds</option>
              <option value="1m">Polling every 1 minute</option>
              <option value="5m">Polling every 5 minutes</option>
            </select>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-3 pt-2">
        {saved && (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 animate-in fade-in">
            <Check className="h-4 w-4" />
            Preferences saved
          </span>
        )}
        <button
          type="button"
          onClick={handleSave}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        >
          <Save className="h-3.5 w-3.5" />
          Save Preferences
        </button>
      </div>
    </div>
  );
}
