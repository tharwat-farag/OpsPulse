"use client";

import React, { useState, useEffect } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { PurchaseOrdersTable } from "@/components/tables/PurchaseOrdersTable";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";
import { formatCurrency } from "@/lib/utils";

export default function ProcurementPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getProcurement();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load procurement metrics from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading procurement and purchase order metrics from PostgreSQL..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Procurement Service Offline"
        error={error || "Failed to connect to procurement API endpoint."}
        onRetry={loadData}
      />
    );
  }

  const totalPoCount = data.statusBreakdown.reduce((sum: number, b: any) => sum + b.count, 0) || 1000;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((metric: any) => (
          <KpiCard key={metric.title} metric={metric} />
        ))}
      </div>

      {/* PO Status Breakdown Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {data.statusBreakdown.map((item: any) => (
          <div key={item.status} className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">{item.status}</span>
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: item.color }}
              />
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-xl font-bold text-slate-900">{item.count} Orders</span>
              <span className="text-xs font-semibold text-slate-600">{formatCurrency(item.value)}</span>
            </div>
            <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(item.count / totalPoCount) * 100}%`,
                  backgroundColor: item.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Purchase Orders Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Purchase Order Registry</h3>
          <p className="text-xs text-slate-500">
            Automated procurement pipeline tracking 1,000 purchase orders and 1,453 goods receipts from PostgreSQL
          </p>
        </div>
        <PurchaseOrdersTable orders={data.purchaseOrders} />
      </div>
    </div>
  );
}
