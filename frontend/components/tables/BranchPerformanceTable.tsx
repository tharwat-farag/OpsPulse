import React from "react";
import { BranchPerformance } from "@/types";
import { StatusBadge } from "../ui/StatusBadge";
import { formatCurrency, formatNumber } from "@/lib/utils";

interface BranchPerformanceTableProps {
  branches: BranchPerformance[];
}

export const BranchPerformanceTable: React.FC<BranchPerformanceTableProps> = ({ branches }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <tr>
            <th className="py-3 px-4">Branch</th>
            <th className="py-3 px-4">Region</th>
            <th className="py-3 px-4 text-right">Orders</th>
            <th className="py-3 px-4 text-right">MTD Revenue</th>
            <th className="py-3 px-4 text-right">Target Achieved</th>
            <th className="py-3 px-4 text-center">Health</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {branches.map((b) => (
            <tr key={b.branchId} className="hover:bg-slate-50/80 transition-colors">
              <td className="py-3 px-4 font-semibold text-slate-900">{b.branchName}</td>
              <td className="py-3 px-4 text-slate-600">{b.region}</td>
              <td className="py-3 px-4 text-right font-medium text-slate-800">
                {formatNumber(b.orders)}
              </td>
              <td className="py-3 px-4 text-right font-bold text-slate-900">
                {formatCurrency(b.revenue)}
              </td>
              <td className="py-3 px-4 text-right font-semibold text-slate-800">
                {b.targetAchievementPct}%
              </td>
              <td className="py-3 px-4 text-center">
                <StatusBadge status={b.status} size="sm" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
