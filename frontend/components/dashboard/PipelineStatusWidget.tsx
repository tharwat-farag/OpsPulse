import React from "react";
import Link from "next/link";
import { PipelineRun } from "@/types";
import { StatusBadge } from "../ui/StatusBadge";
import { CheckCircle2, ArrowRight, Clock, Database, Layers } from "lucide-react";

interface PipelineStatusWidgetProps {
  latestRun: PipelineRun;
}

export const PipelineStatusWidget: React.FC<PipelineStatusWidgetProps> = ({ latestRun }) => {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Airflow 3.4.0 Engine</h4>
            <p className="text-[10px] text-slate-500 font-mono">DAG: {latestRun.dagId}</p>
          </div>
        </div>
        <StatusBadge status={latestRun.status} size="sm" />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            <span className="text-[10px] uppercase font-semibold">Duration</span>
          </div>
          <span className="mt-1 block font-bold text-slate-900">
            {latestRun.durationSeconds.toFixed(2)}s
          </span>
        </div>

        <div className="rounded-lg bg-slate-50 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Layers className="h-3.5 w-3.5" />
            <span className="text-[10px] uppercase font-semibold">Tasks Completed</span>
          </div>
          <span className="mt-1 block font-bold text-slate-900">
            {latestRun.tasksSucceeded} / {latestRun.tasksTotal}
          </span>
        </div>

        <div className="rounded-lg bg-slate-50 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Database className="h-3.5 w-3.5" />
            <span className="text-[10px] uppercase font-semibold">Batch Association</span>
          </div>
          <span className="mt-1 block font-mono text-[11px] font-bold text-blue-600 truncate">
            {latestRun.batchId.replace("batch_", "")}
          </span>
        </div>

        <div className="rounded-lg bg-slate-50 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-[10px] uppercase font-semibold">Warehouse Target</span>
          </div>
          <span className="mt-1 block font-bold text-slate-900">PostgreSQL DW</span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs">
        <span className="text-[11px] text-slate-400">
          Last run started at {latestRun.startTime}
        </span>
        <Link
          href="/monitoring"
          className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-800 transition"
        >
          <span>View Telemetry Breakdown</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
};
