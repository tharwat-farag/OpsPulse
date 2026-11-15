"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";
import { InventoryItem } from "@/types";
import { formatCurrency, formatNumber } from "@/lib/utils";

interface InventoryTableProps {
  items: InventoryItem[];
}

export const InventoryTable: React.FC<InventoryTableProps> = ({ items }) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [warehouseFilter, setWarehouseFilter] = useState("all");
  const [sortField, setSortField] = useState<keyof InventoryItem>("totalValue");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const warehouses = useMemo(() => {
    return Array.from(new Set(items.map((i) => i.warehouseName)));
  }, [items]);

  const filteredItems = useMemo(() => {
    return items
      .filter((i) => {
        const matchesSearch =
          i.sku.toLowerCase().includes(search.toLowerCase()) ||
          i.productName.toLowerCase().includes(search.toLowerCase()) ||
          i.category.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === "all" || i.status === statusFilter;
        const matchesWarehouse = warehouseFilter === "all" || i.warehouseName === warehouseFilter;
        return matchesSearch && matchesStatus && matchesWarehouse;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [items, search, statusFilter, warehouseFilter, sortField, sortDirection]);

  const toggleSort = (field: keyof InventoryItem) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <SearchFilter
          value={search}
          onChange={setSearch}
          placeholder="Search by SKU, product, category..."
          className="w-full sm:w-72"
        />

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="optimal">Optimal</option>
            <option value="low_stock">Low Stock</option>
            <option value="out_of_stock">Out of Stock</option>
            <option value="overstocked">Overstocked</option>
          </select>

          <select
            value={warehouseFilter}
            onChange={(e) => setWarehouseFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Warehouses</option>
            {warehouses.map((w) => (
              <option key={w} value={w}>
                {w}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <EmptyState
          title="No inventory items found"
          description="Adjust your search filters to find matching stock records."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearch("");
            setStatusFilter("all");
            setWarehouseFilter("all");
          }}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("sku")}
                >
                  <div className="flex items-center gap-1">
                    <span>SKU / Product</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th className="py-3 px-4">Warehouse Facility</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("quantityOnHand")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>On Hand</span>
                    {sortField === "quantityOnHand" ? (
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
                <th className="py-3 px-4 text-right">Safety Stock</th>
                <th className="py-3 px-4 text-right">Unit Cost</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("totalValue")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Total Value</span>
                    {sortField === "totalValue" ? (
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
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredItems.map((item) => (
                <tr key={item.sku} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-900 block">{item.productName}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{item.sku} &bull; {item.category}</span>
                  </td>
                  <td className="py-3 px-4 text-slate-600">{item.warehouseName}</td>
                  <td className="py-3 px-4 text-right font-medium text-slate-900">
                    {formatNumber(item.quantityOnHand)}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-500">
                    {formatNumber(item.safetyStock)}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-600">
                    {formatCurrency(item.unitCost)}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-slate-900">
                    {formatCurrency(item.totalValue)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={item.status} size="sm" />
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
