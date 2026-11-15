"use client";

import React, { useState, useMemo } from "react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { formatNumber } from "@/lib/utils";

interface DqCheckDetail {
  checkId: string;
  dataset: string;
  checkType: string;
  ruleName: string;
  columnName: string;
  status: string;
  recordsTested: number;
  violationCount: number;
  violationPct: number;
}

interface DqChecksTableProps {
  checks: DqCheckDetail[];
}

export const DqChecksTable: React.FC<DqChecksTableProps> = ({ checks }) => {
  const [search, setSearch] = useState("");
  const [datasetFilter, setDatasetFilter] = useState("all");

  const datasets = useMemo(() => {
    return Array.from(new Set(checks.map((c) => c.dataset)));
  }, [checks]);

  const filteredChecks = useMemo(() => {
    return checks.filter((c) => {
      const matchesSearch =
        c.ruleName.toLowerCase().includes(search.toLowerCase()) ||
        c.columnName.toLowerCase().includes(search.toLowerCase()) ||
        c.checkId.toLowerCase().includes(search.toLowerCase());
      const matchesDataset = datasetFilter === "all" || c.dataset === datasetFilter;
      return matchesSearch && matchesDataset;
    });
  }, [checks, search, datasetFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <SearchFilter
          value={search}
          onChange={setSearch}
          placeholder="Search rule name or column..."
          className="w-full sm:w-72"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Dataset:</label>
          <select
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All 12 Datasets</option>
            {datasets.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <tr>
              <th className="py-3 px-4">Check ID</th>
              <th className="py-3 px-4">Dataset</th>
              <th className="py-3 px-4">Rule Name</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Target Column</th>
              <th className="py-3 px-4 text-right">Tested Rows</th>
              <th className="py-3 px-4 text-right">Violations</th>
              <th className="py-3 px-4 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredChecks.map((chk) => (
              <tr key={chk.checkId} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 px-4 font-mono font-bold text-slate-700">{chk.checkId}</td>
                <td className="py-3 px-4 font-semibold text-blue-600">{chk.dataset}</td>
                <td className="py-3 px-4 font-mono text-slate-900">{chk.ruleName}</td>
                <td className="py-3 px-4 text-slate-600">{chk.checkType}</td>
                <td className="py-3 px-4 font-mono text-slate-500">{chk.columnName}</td>
                <td className="py-3 px-4 text-right font-medium text-slate-800">
                  {formatNumber(chk.recordsTested)}
                </td>
                <td className="py-3 px-4 text-right font-medium text-emerald-600">
                  {chk.violationCount} ({chk.violationPct}%)
                </td>
                <td className="py-3 px-4 text-center">
                  <StatusBadge status={chk.status} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
