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
  Cell,
} from "recharts";
import { DataVolumeLineage } from "@/types";
import { formatNumber } from "@/lib/utils";

interface VolumeLineageChartProps {
  data: DataVolumeLineage[];
  className?: string;
}

const LAYER_COLORS: Record<string, string> = {
  Raw: "#94A3B8",
  Bronze: "#B45309",
  Silver: "#64748B",
  Quarantine: "#EF4444",
  Gold: "#F59E0B",
};

export const VolumeLineageChart: React.FC<VolumeLineageChartProps> = ({ data, className }) => {
  return (
    <div className={className}>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
            <XAxis dataKey="layer" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis
              stroke="#94A3B8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v / 1000}k`}
            />
            <Tooltip
              formatter={(value: number, _, props: any) => [
                `${formatNumber(value)} records`,
                `Audit Source: ${props.payload.source}`,
              ]}
              contentStyle={{
                backgroundColor: "#0F172A",
                borderColor: "#1E293B",
                borderRadius: "8px",
                color: "#F8FAFC",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="recordCount" radius={[4, 4, 0, 0]} barSize={36}>
              {data.map((entry) => (
                <Cell key={entry.layer} fill={LAYER_COLORS[entry.layer] || "#2563EB"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
