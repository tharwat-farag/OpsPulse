"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";
import { SupplierMetric } from "@/types";
import { formatCurrency } from "@/lib/utils";

interface SuppliersTableProps {
  suppliers: SupplierMetric[];
}

export const SuppliersTable: React.FC<SuppliersTableProps> = ({ suppliers }) => {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [sortField, setSortField] = useState<keyof SupplierMetric>("totalSpendYtd");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const filteredSuppliers = useMemo(() => {
    return suppliers
      .filter((s) => {
        const matchesSearch =
          s.supplierName.toLowerCase().includes(search.toLowerCase()) ||
          s.category.toLowerCase().includes(search.toLowerCase());
        const matchesRisk = riskFilter === "all" || s.riskLevel === riskFilter;
        return matchesSearch && matchesRisk;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [suppliers, search, riskFilter, sortField, sortDirection]);

  const toggleSort = (field: keyof SupplierMetric) => {
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
          placeholder="Search supplier or category..."
          className="w-full sm:w-72"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Risk Tier:</label>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Risk Levels</option>
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
          </select>
        </div>
      </div>

      {filteredSuppliers.length === 0 ? (
        <EmptyState
          title="No suppliers found"
          description="Adjust your search criteria to view matching vendor records."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearch("");
            setRiskFilter("all");
          }}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">Supplier Name</th>
                <th className="py-3 px-4">Category Domain</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("totalSpendYtd")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>YTD Spend</span>
                    {sortField === "totalSpendYtd" ? (
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
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("onTimeDeliveryPct")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>On-Time %</span>
                    {sortField === "onTimeDeliveryPct" ? (
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
                <th className="py-3 px-4 text-right">Fulfillment</th>
                <th className="py-3 px-4 text-center">Score</th>
                <th className="py-3 px-4 text-center">Risk Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredSuppliers.map((s) => (
                <tr key={s.supplierId} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-semibold text-slate-900">{s.supplierName}</td>
                  <td className="py-3 px-4 text-slate-600">{s.category}</td>
                  <td className="py-3 px-4 text-right font-bold text-slate-900">
                    {formatCurrency(s.totalSpendYtd)}
                  </td>
                  <td className="py-3 px-4 text-right font-semibold text-slate-800">
                    {s.onTimeDeliveryPct}%
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-slate-800">
                    {s.fulfillmentRatePct}%
                  </td>
                  <td className="py-3 px-4 text-center font-bold text-amber-600">
                    {s.qualityRating} / 5.0
                  </td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={s.riskLevel} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
