"use client";

import React, { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { SearchFilter } from "../ui/SearchFilter";
import { EmptyState } from "../ui/EmptyState";
import { OperatingExpenseItem } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface ExpensesTableProps {
  expenses: OperatingExpenseItem[];
}

export const ExpensesTable: React.FC<ExpensesTableProps> = ({ expenses }) => {
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<keyof OperatingExpenseItem>("actualAmount");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const filteredExpenses = useMemo(() => {
    return expenses
      .filter((e) => {
        return (
          e.category.toLowerCase().includes(search.toLowerCase()) ||
          e.branchName.toLowerCase().includes(search.toLowerCase())
        );
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
        if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
  }, [expenses, search, sortField, sortDirection]);

  const toggleSort = (field: keyof OperatingExpenseItem) => {
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
          placeholder="Filter by category or branch..."
          className="w-full sm:w-72"
        />
      </div>

      {filteredExpenses.length === 0 ? (
        <EmptyState
          title="No expenses found"
          description="Clear your filter query to see all operating expense lines."
          actionLabel="Reset Search"
          onAction={() => setSearch("")}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">Expense Category</th>
                <th className="py-3 px-4">Branch / Cost Center</th>
                <th className="py-3 px-4">Period</th>
                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-slate-900"
                  onClick={() => toggleSort("actualAmount")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Actual OpEx</span>
                    {sortField === "actualAmount" ? (
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
                <th className="py-3 px-4 text-right">Budget Plan</th>
                <th className="py-3 px-4 text-right">Variance ($)</th>
                <th className="py-3 px-4 text-right">Variance (%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredExpenses.map((exp) => {
                const isUnderBudget = exp.varianceAmount <= 0;
                return (
                  <tr key={exp.expenseId} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">{exp.category}</td>
                    <td className="py-3 px-4 text-slate-600">{exp.branchName}</td>
                    <td className="py-3 px-4 text-slate-500">{exp.period}</td>
                    <td className="py-3 px-4 text-right font-bold text-slate-900">
                      {formatCurrency(exp.actualAmount)}
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-slate-500">
                      {formatCurrency(exp.budgetAmount)}
                    </td>
                    <td
                      className={cn(
                        "py-3 px-4 text-right font-semibold",
                        isUnderBudget ? "text-emerald-600" : "text-rose-600"
                      )}
                    >
                      {formatCurrency(exp.varianceAmount)}
                    </td>
                    <td
                      className={cn(
                        "py-3 px-4 text-right font-medium",
                        isUnderBudget ? "text-emerald-600" : "text-rose-600"
                      )}
                    >
                      {exp.variancePct > 0 ? `+${exp.variancePct}%` : `${exp.variancePct}%`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
