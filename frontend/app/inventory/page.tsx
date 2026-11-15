"use client";

import React, { useState, useEffect } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { InventoryTable } from "@/components/tables/InventoryTable";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";
import { formatCurrency, formatNumber } from "@/lib/utils";
import { Warehouse, MapPin } from "lucide-react";

export default function InventoryPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getInventory();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load inventory metrics from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading inventory valuation and stock health from PostgreSQL..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Inventory Service Offline"
        error={error || "Failed to connect to inventory API."}
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

      {/* Warehouse Facilities Distribution */}
      <div>
        <div className="mb-3">
          <h3 className="text-sm font-bold text-slate-900">Distribution Facility Capacity & Utilization</h3>
          <p className="text-xs text-slate-500">Live square footage usage and inventory valuation per warehouse site</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.warehouses.map((wh: any) => (
            <div key={wh.warehouseId} className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                  <Warehouse className="h-4 w-4" />
                </div>
                <span className="font-mono text-[10px] font-bold text-slate-400">{wh.warehouseId}</span>
              </div>
              <h4 className="mt-3 font-bold text-slate-900 text-xs">{wh.warehouseName}</h4>
              <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-0.5">
                <MapPin className="h-3 w-3 text-slate-400" />
                <span>{wh.location}</span>
              </div>

              <div className="mt-3.5 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Capacity Utilization</span>
                  <span className="font-bold text-slate-900">{wh.utilizationPct}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-blue-600 rounded-full"
                    style={{ width: `${Math.min(100, wh.utilizationPct)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                  <span>{formatNumber(wh.skuCount)} SKUs</span>
                  <span className="font-semibold text-slate-700">{formatCurrency(wh.totalInventoryValue)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Inventory Item Health Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Inventory Items & SKU Stock Health</h3>
          <p className="text-xs text-slate-500">
            Latest available warehouse snapshot from PostgreSQL gold.fact_inventory_snapshot (date_key = 20251231)
          </p>
        </div>
        <InventoryTable items={data.items} />
      </div>
    </div>
  );
}
