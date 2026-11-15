import React from "react";
import { ProductPerformance } from "@/types";
import { StatusBadge } from "../ui/StatusBadge";
import { formatCurrency, formatNumber } from "@/lib/utils";

interface TopProductsTableProps {
  products: ProductPerformance[];
}

export const TopProductsTable: React.FC<TopProductsTableProps> = ({ products }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <tr>
            <th className="py-3 px-4">Product Name / SKU</th>
            <th className="py-3 px-4">Category</th>
            <th className="py-3 px-4 text-right">Units Sold</th>
            <th className="py-3 px-4 text-right">Revenue</th>
            <th className="py-3 px-4 text-right">Margin</th>
            <th className="py-3 px-4 text-center">Stock Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {products.map((p) => (
            <tr key={p.productId} className="hover:bg-slate-50/80 transition-colors">
              <td className="py-3 px-4">
                <span className="font-semibold text-slate-900 block">{p.productName}</span>
                <span className="text-[10px] text-slate-400 font-mono">{p.sku}</span>
              </td>
              <td className="py-3 px-4 text-slate-600">{p.category}</td>
              <td className="py-3 px-4 text-right font-medium text-slate-900">
                {formatNumber(p.unitsSold)}
              </td>
              <td className="py-3 px-4 text-right font-bold text-slate-900">
                {formatCurrency(p.revenue)}
              </td>
              <td className="py-3 px-4 text-right font-medium text-emerald-600">
                {p.marginPct}%
              </td>
              <td className="py-3 px-4 text-center">
                <StatusBadge status={p.stockStatus} size="sm" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
