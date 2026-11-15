"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { BranchPerformance } from "@/types";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";

interface BranchBarChartProps {
  data: BranchPerformance[];
  className?: string;
}

export const BranchBarChart: React.FC<BranchBarChartProps> = ({ data, className }) => {
  return (
    <div className={className}>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 10, right: 20, left: 30, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0" />
            <XAxis
              type="number"
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => formatCompactCurrency(v)}
            />
            <YAxis
              type="category"
              dataKey="branchName"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={140}
            />
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), "MTD Revenue"]}
              contentStyle={{
                backgroundColor: "#0F172A",
                borderColor: "#1E293B",
                borderRadius: "8px",
                color: "#F8FAFC",
                fontSize: "12px",
              }}
            />
            <Bar
              dataKey="revenue"
              fill="#2563EB"
              radius={[0, 4, 4, 0]}
              barSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
