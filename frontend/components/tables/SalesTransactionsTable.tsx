"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";
import { formatCurrency } from "@/lib/utils";

interface Transaction {
  id: string;
  date: string;
  customer: string;
  branch: string;
  channel: string;
  itemsCount: number;
  grossAmount: number;
  discountAmount: number;
  netAmount: number;
  paymentMethod: string;
  status: string;
}

interface SalesTransactionsTableProps {
  transactions: Transaction[];
}

export const SalesTransactionsTable: React.FC<SalesTransactionsTableProps> = ({
  transactions,
}) => {
  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");
  const [sortField, setSortField] = useState<keyof Transaction>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const channels = useMemo(() => {
    return Array.from(new Set(transactions.map((t) => t.channel)));
  }, [transactions]);

  const filteredTransactions = useMemo(() => {
    return transactions
      .filter((t) => {
        const matchesSearch =
          t.id.toLowerCase().includes(search.toLowerCase()) ||
          t.customer.toLowerCase().includes(search.toLowerCase()) ||
          t.branch.toLowerCase().includes(search.toLowerCase());
        const matchesChannel = channelFilter === "all" || t.channel === channelFilter;
        return matchesSearch && matchesChannel;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [transactions, search, channelFilter, sortField, sortDirection]);

  const toggleSort = (field: keyof Transaction) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Table controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <SearchFilter
          value={search}
          onChange={setSearch}
          placeholder="Search by ID, customer, branch..."
          className="w-full sm:w-72"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Channel:</label>
          <select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Channels</option>
            {channels.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredTransactions.length === 0 ? (
        <EmptyState
          title="No transactions found"
          description="Try clearing your search query or channel filter."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearch("");
            setChannelFilter("all");
          }}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("id")}
                >
                  <div className="flex items-center gap-1">
                    <span>Transaction ID</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("date")}
                >
                  <div className="flex items-center gap-1">
                    <span>Timestamp</span>
                    {sortField === "date" ? (
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
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Branch / Channel</th>
                <th className="py-3 px-4 text-right">Items</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("netAmount")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Net Amount</span>
                    {sortField === "netAmount" ? (
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
              {filteredTransactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-blue-600">{tx.id}</td>
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">{tx.date}</td>
                  <td className="py-3 px-4 font-medium text-slate-900">{tx.customer}</td>
                  <td className="py-3 px-4">
                    <span className="font-medium text-slate-800 block">{tx.branch}</span>
                    <span className="text-[10px] text-slate-400">{tx.channel}</span>
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-slate-800">
                    {tx.itemsCount}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-slate-900">
                    {formatCurrency(tx.netAmount)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <StatusBadge status={tx.status} size="sm" />
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
