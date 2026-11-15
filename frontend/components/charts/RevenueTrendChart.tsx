"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { RevenueTrendPoint } from "@/types";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";

interface RevenueTrendChartProps {
  data: RevenueTrendPoint[];
  className?: string;
}

export const RevenueTrendChart: React.FC<RevenueTrendChartProps> = ({ data, className }) => {
  return (
    <div className={className}>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#94A3B8" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#94A3B8" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
            <XAxis
              dataKey="date"
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => formatCompactCurrency(v)}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name === "revenue"
                  ? "Net Revenue"
                  : name === "target"
                  ? "Revenue Target"
                  : "Operating Cost",
              ]}
              contentStyle={{
                backgroundColor: "#0F172A",
                borderColor: "#1E293B",
                borderRadius: "8px",
                color: "#F8FAFC",
                fontSize: "12px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
              labelStyle={{ color: "#94A3B8", fontWeight: 600, marginBottom: "4px" }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: "12px", paddingBottom: "10px" }}
              formatter={(val) =>
                val === "revenue" ? "Net Revenue" : val === "target" ? "Target" : "COGS & Cost"
              }
            />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#2563EB"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#revenueGradient)"
            />
            <Area
              type="monotone"
              dataKey="cost"
              stroke="#94A3B8"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              fillOpacity={1}
              fill="url(#costGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
