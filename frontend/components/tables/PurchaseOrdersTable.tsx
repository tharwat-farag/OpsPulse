"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";
import { PurchaseOrder } from "@/types";
import { formatCurrency } from "@/lib/utils";

interface PurchaseOrdersTableProps {
  orders: PurchaseOrder[];
}

export const PurchaseOrdersTable: React.FC<PurchaseOrdersTableProps> = ({ orders }) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortField, setSortField] = useState<keyof PurchaseOrder>("orderDate");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const filteredOrders = useMemo(() => {
    return orders
      .filter((po) => {
        const matchesSearch =
          po.poNumber.toLowerCase().includes(search.toLowerCase()) ||
          po.supplierName.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === "all" || po.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [orders, search, statusFilter, sortField, sortDirection]);

  const toggleSort = (field: keyof PurchaseOrder) => {
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
          placeholder="Search by PO number or supplier..."
          className="w-full sm:w-72"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="partially_received">Partially Received</option>
            <option value="received">Received</option>
          </select>
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <EmptyState
          title="No purchase orders found"
          description="Adjust your search query or status filter to see matching orders."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearch("");
            setStatusFilter("all");
          }}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">PO Number</th>
                <th className="py-3 px-4">Supplier Vendor</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("orderDate")}
                >
                  <div className="flex items-center gap-1">
                    <span>Order Date</span>
                    {sortField === "orderDate" ? (
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
                <th className="py-3 px-4">Expected Date</th>
                <th className="py-3 px-4 text-right">Line Items</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("totalAmount")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Committed Total</span>
                    {sortField === "totalAmount" ? (
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
                <th className="py-3 px-4 text-center">Fulfillment</th>
                <th className="py-3 px-4 text-center">Payment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredOrders.map((po) => (
                <tr key={po.poNumber} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-blue-600">{po.poNumber}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">{po.supplierName}</td>
                  <td className="py-3 px-4 text-slate-500">{po.orderDate}</td>
                  <td className="py-3 px-4 text-slate-500">{po.expectedDate}</td>
                  <td className="py-3 px-4 text-right font-medium text-slate-800">
                    {po.lineCount} lines
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-slate-900">
                    {formatCurrency(po.totalAmount)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={po.status} size="sm" />
                  </td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={po.paymentStatus} size="sm" />
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
