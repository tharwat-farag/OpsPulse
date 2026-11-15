"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  Boxes,
  FileCheck,
  Building2,
  Receipt,
  Activity,
  ShieldCheck,
  Settings,
  X,
  Layers,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
}

const PRIMARY_NAV_ITEMS: NavItem[] = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Sales", href: "/sales", icon: TrendingUp },
  { name: "Inventory", href: "/inventory", icon: Boxes },
  { name: "Procurement", href: "/procurement", icon: FileCheck },
  { name: "Suppliers", href: "/suppliers", icon: Building2 },
  { name: "Expenses", href: "/expenses", icon: Receipt },
];

const PLATFORM_NAV_ITEMS: NavItem[] = [
  { name: "Pipeline Monitoring", href: "/monitoring", icon: Activity, badge: "Live" },
  { name: "Data Quality", href: "/data-quality", icon: ShieldCheck, badge: "100%" },
  { name: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#0F172A] border-r border-slate-800 text-slate-300 transition-transform duration-300 ease-in-out lg:static lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand Identity */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-slate-800/80 bg-[#0B1120]">
          <Link href="/" className="flex items-center gap-2.5 focus:outline-none">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-base font-bold tracking-tight text-white">OpsPulse</span>
                <span className="rounded bg-blue-500/20 px-1 py-0.2 text-[10px] font-semibold text-blue-400">
                  v1.0
                </span>
              </div>
              <p className="text-[10px] font-medium text-slate-400">Enterprise Operations</p>
            </div>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Business Intelligence
            </div>
            <nav className="space-y-1">
              {PRIMARY_NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => onClose()}
                    className={cn(
                      "group flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all",
                      isActive
                        ? "bg-blue-600 text-white shadow-sm shadow-blue-600/30 font-semibold"
                        : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={cn(
                          "h-4 w-4 transition-colors",
                          isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"
                        )}
                      />
                      <span>{item.name}</span>
                    </div>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Data Platform & Reliability
            </div>
            <nav className="space-y-1">
              {PLATFORM_NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => onClose()}
                    className={cn(
                      "group flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all",
                      isActive
                        ? "bg-blue-600 text-white shadow-sm shadow-blue-600/30 font-semibold"
                        : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={cn(
                          "h-4 w-4 transition-colors",
                          isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"
                        )}
                      />
                      <span>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                          isActive
                            ? "bg-blue-700 text-white"
                            : item.badge === "Live"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-blue-500/20 text-blue-400"
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Pipeline Environment Status footer card */}
        <div className="p-4 border-t border-slate-800/80 bg-[#0B1120]/60">
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-200">Airflow 3.4.0 Engine</span>
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            </div>
            <p className="mt-1 text-[10px] text-slate-400">Warehouse: PostgreSQL opspulse_dw</p>
            <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-800">
              <span>DAG Status</span>
              <span className="font-semibold text-emerald-400">Healthy (30 Tasks)</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
