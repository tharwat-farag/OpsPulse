"use client";

import React, { useState, useEffect } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { SuppliersTable } from "@/components/tables/SuppliersTable";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";

export default function SuppliersPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getSuppliers();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load supplier performance from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading supplier scorecards and delivery SLAs from PostgreSQL..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Suppliers Service Offline"
        error={error || "Failed to connect to suppliers API endpoint."}
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

      {/* Supplier Directory Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Supplier Scorecard Directory</h3>
          <p className="text-xs text-slate-500">
            Performance scoring, delivery predictability, and annual spend across PostgreSQL gold.dim_supplier
          </p>
        </div>
        <SuppliersTable suppliers={data.directory} />
      </div>
    </div>
  );
}
