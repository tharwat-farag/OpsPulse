"use client";

import React, { useState, useEffect, useCallback } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { RevenueTrendChart } from "@/components/charts/RevenueTrendChart";
import { ChannelSharePieChart } from "@/components/charts/ChannelSharePieChart";
import { BranchBarChart } from "@/components/charts/BranchBarChart";
import { TopProductsTable } from "@/components/tables/TopProductsTable";
import { BranchPerformanceTable } from "@/components/tables/BranchPerformanceTable";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { PipelineStatusWidget } from "@/components/dashboard/PipelineStatusWidget";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";
import { useDateRange } from "@/lib/context/DateRangeContext";
import { ArrowUpRight, Layers } from "lucide-react";
import Link from "next/link";

export default function OverviewPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { year, quarter } = useDateRange();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getOverview({ year, quarter });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load live metrics from PostgreSQL warehouse API.");
    } finally {
      setLoading(false);
    }
  }, [year, quarter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <LoadingState message="Retrieving live executive metrics from PostgreSQL warehouse..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Live Data Service Offline"
        error={error || "Could not retrieve operational data from the API."}
        onRetry={loadData}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Platform Banner */}
      <div className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/80 via-indigo-50/50 to-white p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900">OpsPulse Production Platform</h2>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                  Airflow 3.4.0 Active
                </span>
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                  Live PostgreSQL Warehouse
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Monitoring 5 retail branches, 3 distribution warehouses, and 100 active SKUs across the PostgreSQL warehouse.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/monitoring"
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <span>Pipeline Telemetry</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((metric: any) => (
          <KpiCard key={metric.title} metric={metric} />
        ))}
      </div>

      {/* Primary Analytics Section: Revenue Trend & Channel Share */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Revenue Velocity Trend */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Revenue Velocity & Cost Trajectory</h3>
              <p className="text-xs text-slate-500">Gross revenue vs. monthly target and cost of goods</p>
            </div>
            <Link
              href="/sales"
              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
            >
              <span>Sales Deep Dive</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="mt-4">
            <RevenueTrendChart data={data.revenueTrend} />
          </div>
        </div>

        {/* Sales by Channel */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Sales Channel Distribution</h3>
              <p className="text-xs text-slate-500">Volume share across retail, online, and phone channels</p>
            </div>
          </div>
          <div className="mt-4">
            <ChannelSharePieChart data={data.channelShare} />
          </div>
        </div>
      </div>

      {/* Secondary Analytics Section: Branch Performance & Top Products */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Revenue by Branch Bar Chart */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Revenue by Branch</h3>
              <p className="text-xs text-slate-500">Live fulfillment rankings across 5 branches</p>
            </div>
          </div>
          <div className="mt-4">
            <BranchBarChart data={data.branchPerformance} />
          </div>
        </div>

        {/* Top Selling Products Table */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Top Selling Products</h3>
              <p className="text-xs text-slate-500">Fastest-moving items by revenue and margin velocity</p>
            </div>
            <Link
              href="/inventory"
              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
            >
              <span>Inventory Health</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="mt-3">
            <TopProductsTable products={data.topProducts} />
          </div>
        </div>
      </div>

      {/* Operational Sections: Branch Performance, Pipeline Execution, Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Branch Performance Summary */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Branch Operations Performance</h3>
              <p className="text-xs text-slate-500">Regional sales execution across Egypt operational branches</p>
            </div>
          </div>
          <div className="mt-3">
            <BranchPerformanceTable branches={data.branchPerformance} />
          </div>
        </div>

        {/* Live Pipeline Status & Recent Activity */}
        <div className="space-y-6">
          <PipelineStatusWidget latestRun={data.latestRun} />

          <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-sm font-bold text-slate-900">Operational Activity Feed</h3>
              <span className="text-[10px] font-semibold text-emerald-600 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live Feed
              </span>
            </div>
            <ActivityFeed activities={data.activities} />
          </div>
        </div>
      </div>
    </div>
  );
}
