"use client";

import React, { useState, useEffect, useCallback } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { SalesTransactionsTable } from "@/components/tables/SalesTransactionsTable";
import { RevenueTrendChart } from "@/components/charts/RevenueTrendChart";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";
import { useDateRange } from "@/lib/context/DateRangeContext";
import { formatCurrency } from "@/lib/utils";

export default function SalesPage() {
  const [data, setData] = useState<any>(null);
  const [overviewData, setOverviewData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { year, quarter } = useDateRange();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [salesRes, overviewRes] = await Promise.all([
        opspulseApi.getSales({ year, quarter }),
        opspulseApi.getOverview({ year, quarter }),
      ]);
      setData(salesRes);
      setOverviewData(overviewRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load sales analytics from API.");
    } finally {
      setLoading(false);
    }
  }, [year, quarter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <LoadingState message="Loading sales metrics from PostgreSQL warehouse..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Sales Data Unavailable"
        error={error || "Failed to connect to sales API endpoint."}
        onRetry={loadData}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((metric: any) => (
          <KpiCard key={metric.title} metric={metric} />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Sales Velocity & Monthly Net Revenue</h3>
              <p className="text-xs text-slate-500">Live sales performance across 2025 warehouse data</p>
            </div>
          </div>
          <div className="mt-4">
            <RevenueTrendChart data={overviewData?.revenueTrend || []} />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">Sales by Category</h3>
            <p className="text-xs text-slate-500">Revenue contribution & gross margin</p>
          </div>
          <div className="mt-4 space-y-3.5">
            {data.categoryShare.map((c: any) => (
              <div key={c.category} className="space-y-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-700">{c.category}</span>
                  <span className="font-bold text-slate-900">{formatCurrency(c.revenue)}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <div className="h-1.5 w-4/5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full"
                      style={{ width: `${Math.min(100, (c.revenue / (data.categoryShare[0]?.revenue || 1)) * 100)}%` }}
                    />
                  </div>
                  <span className="text-emerald-600 font-semibold">{c.margin}% margin</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Recent Sales Transactions</h3>
          <p className="text-xs text-slate-500">
            Real-time transaction log querying 20,000 sales lines from PostgreSQL gold.fact_sales
          </p>
        </div>
        <SalesTransactionsTable transactions={data.transactions} />
      </div>
    </div>
  );
}
