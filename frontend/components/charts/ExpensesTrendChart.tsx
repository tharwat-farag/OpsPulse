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
  Legend,
} from "recharts";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";

interface ExpensesTrendChartProps {
  data: { month: string; actual: number; budget: number }[];
  className?: string;
}

export const ExpensesTrendChart: React.FC<ExpensesTrendChartProps> = ({ data, className }) => {
  return (
    <div className={className}>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
            <XAxis dataKey="month" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
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
                name === "actual" ? "Actual OpEx" : "Budget Cap",
              ]}
              contentStyle={{
                backgroundColor: "#0F172A",
                borderColor: "#1E293B",
                borderRadius: "8px",
                color: "#F8FAFC",
                fontSize: "12px",
              }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: "12px", paddingBottom: "10px" }}
              formatter={(v) => (v === "actual" ? "Actual Expenses" : "Budget Target")}
            />
            <Bar dataKey="actual" fill="#2563EB" radius={[4, 4, 0, 0]} barSize={22} />
            <Bar dataKey="budget" fill="#CBD5E1" radius={[4, 4, 0, 0]} barSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
