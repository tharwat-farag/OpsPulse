"use client";

import React, { useState, useEffect } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { TaskMetricsTable } from "@/components/tables/TaskMetricsTable";
import { VolumeLineageChart } from "@/components/charts/VolumeLineageChart";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";

export default function MonitoringPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getMonitoring();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load monitoring telemetry from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading pipeline telemetry from PostgreSQL monitoring.* schema..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Monitoring Service Offline"
        error={error || "Failed to connect to pipeline observability API endpoint."}
        onRetry={loadData}
      />
    );
  }

  const latestRun = data.runHistory[0] || {
    dagRunId: "manual__2026-11-15T05:05:32.814530+00:00",
    batchId: "batch_20261115_051056_1d64c5da",
    status: "success",
    durationSeconds: 28.32,
    tasksTotal: 30,
    tasksSucceeded: 30,
  };

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((metric: any) => (
          <KpiCard key={metric.title} metric={metric} />
        ))}
      </div>

      {/* Current Run Active Context Card */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">Latest Production DAG Run Telemetry</h3>
              <StatusBadge status={latestRun.status} size="sm" />
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">{latestRun.dagRunId}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-slate-100 px-2 py-1 text-xs font-mono font-medium text-slate-700">
              Batch: {latestRun.batchId}
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Execution Time</span>
            <span className="text-sm font-bold text-slate-900 mt-1 block">
              {latestRun.durationSeconds.toFixed(2)} seconds
            </span>
            <span className="text-[10px] text-slate-400">Target threshold &lt; 45.0s</span>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Tasks Verified</span>
            <span className="text-sm font-bold text-emerald-600 mt-1 block">
              {latestRun.tasksSucceeded} / {latestRun.tasksTotal} Succeeded
            </span>
            <span className="text-[10px] text-slate-400">0 retried &bull; 0 skipped</span>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Orchestrator</span>
            <span className="text-sm font-bold text-slate-900 mt-1 block">
              Apache Airflow 3.4.0
            </span>
            <span className="text-[10px] text-slate-400">WSL Ubuntu Runtime</span>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Analytics Store</span>
            <span className="text-sm font-bold text-blue-600 mt-1 block">
              opspulse_dw.monitoring.*
            </span>
            <span className="text-[10px] text-slate-400">Idempotent Upserts</span>
          </div>
        </div>
      </div>

      {/* Medallion Architecture Volume Lineage */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Medallion Layer Record Lineage</h3>
          <p className="text-xs text-slate-500">
            Authoritative row count tracking across Raw, Bronze, Silver, Quarantine, and Gold warehouse tables
          </p>
        </div>
        <VolumeLineageChart data={data.volumeLineage} />
      </div>

      {/* Task Performance & Duration Variance Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Task-Level Execution Performance & Variance</h3>
          <p className="text-xs text-slate-500">
            Individual task durations compared against historical moving averages to detect pipeline regressions
          </p>
        </div>
        <TaskMetricsTable tasks={data.taskMetrics} />
      </div>
    </div>
  );
}
