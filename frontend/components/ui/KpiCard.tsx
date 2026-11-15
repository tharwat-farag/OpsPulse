import React from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingBag,
  Boxes,
  AlertTriangle,
  FileText,
  Activity,
  CheckCircle,
  CheckCircle2,
  ShieldCheck,
  Building2,
  Truck,
  RotateCw,
  Layers,
  Database,
  Server,
  LockOpen,
  Receipt,
  PieChart,
  Tag,
  Users,
  RotateCcw,
  Zap,
  Building,
  Star,
  Timer,
  Check,
  CheckCheck,
  PackageCheck,
  Clock,
  Clock4,
  Warehouse,
  XCircle,
} from "lucide-react";
import { KpiMetric } from "@/types";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
  DollarSign,
  TrendingUp,
  TrendingDown,
  ShoppingBag,
  Boxes,
  AlertTriangle,
  FileText,
  Activity,
  CheckCircle,
  CheckCircle2,
  ShieldCheck,
  Building2,
  Truck,
  RotateCw,
  Layers,
  Database,
  Server,
  LockOpen,
  Receipt,
  PieChart,
  Tag,
  Users,
  RotateCcw,
  Zap,
  Building,
  Star,
  Timer,
  Check,
  CheckCheck,
  PackageCheck,
  Clock,
  Clock4,
  Warehouse,
  XCircle,
};

interface KpiCardProps {
  metric: KpiMetric;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({ metric, className }) => {
  const IconComponent = ICON_MAP[metric.iconName] || Activity;
  const isPositive = metric.isPositive;

  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all hover:border-slate-300 hover:shadow-md",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2 min-h-[32px]">
        <span
          className="text-[11px] font-semibold uppercase tracking-normal text-slate-500 line-clamp-2 leading-tight"
          title={metric.title}
        >
          {metric.title}
        </span>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
          <IconComponent className="h-3.5 w-3.5" />
        </div>
      </div>

      <div className="mt-2.5 flex items-baseline justify-between">
        <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">{metric.value}</h3>
      </div>

      <div className="mt-2 flex items-center gap-1.5 text-xs">
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-semibold",
            isPositive
              ? "bg-emerald-50 text-emerald-700"
              : "bg-rose-50 text-rose-700"
          )}
        >
          {metric.trend === "up" ? (
            <TrendingUp className="h-3 w-3" />
          ) : metric.trend === "down" ? (
            <TrendingDown className="h-3 w-3" />
          ) : null}
          {metric.changePct > 0 ? `+${metric.changePct}%` : `${metric.changePct}%`}
        </span>
        <span
          className="text-[11px] text-slate-500 truncate"
          title={metric.caption}
        >
          {metric.caption}
        </span>
      </div>
    </div>
  );
};
