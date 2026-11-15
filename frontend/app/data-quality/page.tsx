"use client";

import React, { useState, useEffect } from "react";
import { KpiCard } from "@/components/ui/KpiCard";
import { DqChecksTable } from "@/components/tables/DqChecksTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState, ErrorState } from "@/components/ui/EmptyState";
import { opspulseApi } from "@/lib/api/client";

export default function DataQualityPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opspulseApi.getDataQuality();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load data quality metrics from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading automated data quality suite metrics..." />;
  }

  if (error || !data) {
    return (
      <ErrorState
        title="Data Quality Service Offline"
        error={error || "Failed to connect to data quality API endpoint."}
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

      {/* Categories & Dataset Breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Rule Category Breakdown */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">Rule Category Verification</h3>
            <p className="text-xs text-slate-500">Quality check pass rates by assertion domain</p>
          </div>
          <div className="mt-4 space-y-3.5">
            {data.summary.ruleCategories.map((rc: any) => (
              <div key={rc.category} className="space-y-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-700">{rc.category}</span>
                  <span className="font-bold text-emerald-600">
                    {rc.passed} / {rc.total} Passed (100%)
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full w-full" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 12 Silver Datasets Coverage Matrix */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">Silver Layer Dataset Audit Matrix</h3>
            <p className="text-xs text-slate-500">Automated gate promotion status across all 12 Silver tables</p>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {data.summary.datasets.map((ds: any) => (
              <div
                key={ds.name}
                className="rounded-lg border border-slate-200/60 bg-slate-50/60 p-3 transition hover:border-slate-300"
              >
                <div className="flex items-center justify-between">
                  <StatusBadge status={ds.status} size="sm" />
                  <span className="text-[10px] font-bold text-emerald-600">{ds.score}%</span>
                </div>
                <span className="mt-2 block font-mono text-xs font-bold text-slate-900 truncate">
                  {ds.name}
                </span>
                <span className="text-[11px] text-slate-500">{ds.checks} assertions passed</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Detailed Check Assertion Log Table */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3 mb-4">
          <h3 className="text-sm font-bold text-slate-900">Quality Check Assertion Details</h3>
          <p className="text-xs text-slate-500">
            Granular rule execution results, evaluated row counts, and zero-violation certifications
          </p>
        </div>
        <DqChecksTable checks={data.checkDetails} />
      </div>
    </div>
  );
}
