"use client";

import React, { useState, useEffect, useCallback } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { ExpensesTable } from "@/components/tables/ExpensesTable";
import { ExpensesTrendChart } from "@/components/charts/ExpensesTrendChart";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";
import { useDateRange } from "@/lib/context/DateRangeContext";
import { formatCurrency } from "@/lib/utils";

export default function ExpensesPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { year, quarter } = useDateRange();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getExpenses({ year, quarter });
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load operating expenses from API.");
    } finally {
      setLoading(false);
    }
  }, [year, quarter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <LoadingState message="Loading operating expenses from PostgreSQL gold.fact_operating_expenses..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Expenses Service Offline"
        error={error || "Failed to connect to operating expenses API endpoint."}
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
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">Monthly Operating Expenses vs. Allocated Budget</h3>
            <p className="text-xs text-slate-500">Trailing budget adherence across 2,000 real expense records</p>
          </div>
          <div className="mt-4">
            <ExpensesTrendChart data={data.monthlyTrend} />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">Expenses by Cost Category</h3>
            <p className="text-xs text-slate-500">Spend breakdown across 5 expense categories</p>
          </div>
          <div className="mt-4 space-y-3">
            {data.categories.map((c: any) => (
              <div key={c.category} className="space-y-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-700 truncate">{c.category}</span>
                  <span className="font-bold text-slate-900">{formatCurrency(c.actual)}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <div className="h-1.5 w-4/5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full"
                      style={{ width: `${Math.min(100, c.share)}%` }}
                    />
                  </div>
                  <span>{c.share}% share</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Operating Expenses Ledger</h3>
          <p className="text-xs text-slate-500">
            Real branch cost allocations from gold.fact_operating_expenses
          </p>
        </div>
        <ExpensesTable expenses={data.expenses} />
      </div>
    </div>
  );
}
