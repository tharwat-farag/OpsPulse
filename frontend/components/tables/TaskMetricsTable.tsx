"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { TaskMetric } from "@/types";
import { cn } from "@/lib/utils";

interface TaskMetricsTableProps {
  tasks: TaskMetric[];
}

export const TaskMetricsTable: React.FC<TaskMetricsTableProps> = ({ tasks }) => {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sortField, setSortField] = useState<keyof TaskMetric>("durationSeconds");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const categories = useMemo(() => {
    return Array.from(new Set(tasks.map((t) => t.category)));
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    return tasks
      .filter((t) => {
        const matchesSearch = t.taskId.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = categoryFilter === "all" || t.category === categoryFilter;
        return matchesSearch && matchesCategory;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [tasks, search, categoryFilter, sortField, sortDirection]);

  const toggleSort = (field: keyof TaskMetric) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <SearchFilter
          value={search}
          onChange={setSearch}
          placeholder="Search task ID..."
          className="w-full sm:w-72"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Stage:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Stages</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <tr>
              <th className="py-3 px-4">Task Identifier</th>
              <th className="py-3 px-4">Pipeline Stage</th>
              <th
                className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                onClick={() => toggleSort("durationSeconds")}
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Duration</span>
                  {sortField === "durationSeconds" ? (
                    sortDirection === "asc" ? (
                      <ArrowUp className="h-3 w-3 text-blue-600" />
                    ) : (
                      <ArrowDown className="h-3 w-3 text-blue-600" />
                    )
                  ) : (
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  )}
                </div>
              </th>
              <th className="py-3 px-4 text-right">Historical Avg</th>
              <th className="py-3 px-4 text-right">Variance (%)</th>
              <th className="py-3 px-4 text-center">Attempt</th>
              <th className="py-3 px-4 text-center">State</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredTasks.map((t) => (
              <tr key={t.taskId} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 px-4 font-mono font-bold text-slate-900">{t.taskId}</td>
                <td className="py-3 px-4 text-slate-600">{t.category}</td>
                <td className="py-3 px-4 text-right font-bold text-slate-900">
                  {t.durationSeconds.toFixed(2)}s
                </td>
                <td className="py-3 px-4 text-right text-slate-500">
                  {t.historicalAvgSeconds.toFixed(2)}s
                </td>
                <td
                  className={cn(
                    "py-3 px-4 text-right font-medium",
                    t.variancePct > 5
                      ? "text-rose-600"
                      : t.variancePct < -5
                      ? "text-emerald-600"
                      : "text-slate-600"
                  )}
                >
                  {t.variancePct > 0 ? `+${t.variancePct}%` : `${t.variancePct}%`}
                </td>
                <td className="py-3 px-4 text-center font-medium text-slate-600">
                  #{t.tryNumber}
                </td>
                <td className="py-3 px-4 text-center">
                  <StatusBadge status={t.state} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
