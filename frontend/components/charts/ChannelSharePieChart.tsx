"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { ChannelShare } from "@/types";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";

interface ChannelSharePieChartProps {
  data: ChannelShare[];
  className?: string;
}

export const ChannelSharePieChart: React.FC<ChannelSharePieChartProps> = ({
  data,
  className,
}) => {
  return (
    <div className={className}>
      <div className="flex h-64 flex-col sm:flex-row items-center justify-between gap-4">
        <div className="h-48 w-48 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={76}
                paddingAngle={3}
                dataKey="revenue"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="#FFFFFF" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [formatCurrency(value), "Revenue"]}
                contentStyle={{
                  backgroundColor: "#0F172A",
                  borderColor: "#1E293B",
                  borderRadius: "8px",
                  color: "#F8FAFC",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="w-full flex-1 space-y-2">
          {data.map((item) => (
            <div key={item.channel} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="font-medium text-slate-700">{item.channel}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900" title={formatCurrency(item.revenue)}>
                  {formatCompactCurrency(item.revenue)}
                </span>
                <span className="w-9 text-right font-medium text-slate-400">
                  {item.percentage}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
