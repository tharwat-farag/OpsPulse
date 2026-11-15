import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
  size?: "sm" | "md";
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  size = "md",
  className,
}) => {
  // Infer variant if not explicitly provided
  const resolvedVariant = variant || inferVariant(status);

  const variantStyles = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    danger: "bg-rose-50 text-rose-700 border-rose-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
  }[resolvedVariant];

  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs font-medium",
  }[size];

  const label = formatStatusLabel(status);

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border capitalize tracking-wide transition-colors",
        variantStyles,
        sizeStyles,
        className
      )}
    >
      <span
        className={cn("mr-1.5 h-1.5 w-1.5 rounded-full", {
          "bg-emerald-500": resolvedVariant === "success",
          "bg-amber-500": resolvedVariant === "warning",
          "bg-rose-500": resolvedVariant === "danger",
          "bg-blue-500": resolvedVariant === "info",
          "bg-slate-400": resolvedVariant === "neutral",
        })}
      />
      {label}
    </span>
  );
};

function inferVariant(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  const s = status.toLowerCase();
  if (
    s.includes("success") ||
    s.includes("optimal") ||
    s.includes("in_stock") ||
    s.includes("received") ||
    s.includes("completed") ||
    s.includes("exceeding") ||
    s.includes("paid") ||
    s.includes("pass") ||
    s.includes("promoted") ||
    s.includes("low") // low risk
  ) {
    return "success";
  }
  if (
    s.includes("low_stock") ||
    s.includes("partially") ||
    s.includes("pending") ||
    s.includes("draft") ||
    s.includes("warn") ||
    s.includes("medium") // medium risk
  ) {
    return "warning";
  }
  if (
    s.includes("out_of_stock") ||
    s.includes("fail") ||
    s.includes("underperforming") ||
    s.includes("cancelled") ||
    s.includes("overdue") ||
    s.includes("high") // high risk
  ) {
    return "danger";
  }
  if (s.includes("submitted") || s.includes("on_track") || s.includes("running") || s.includes("info")) {
    return "info";
  }
  return "neutral";
}

function formatStatusLabel(status: string): string {
  return status.replace(/_/g, " ");
}
