"use client";

import React, { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import {
  Menu,
  Bell,
  Check,
  ChevronRight,
  Shield,
  Activity,
  User,
  LogOut,
  ExternalLink,
  ChevronDown,
} from "lucide-react";
import { DateRangePicker } from "../ui/DateRangePicker";
import { DateRangeOption } from "@/types";
import { NOTIFICATIONS_DATA } from "@/lib/mock-data/notifications";
import { cn } from "@/lib/utils";

interface TopNavProps {
  onToggleSidebar: () => void;
  dateRange: DateRangeOption;
  onDateRangeChange: (val: DateRangeOption) => void;
}

const PAGE_TITLES: Record<string, { title: string; subtitle: string; category: string }> = {
  "/": {
    title: "Executive Overview",
    subtitle: "High-level retail operations, revenue velocity, and warehouse health",
    category: "Business Intelligence",
  },
  "/sales": {
    title: "Sales & Revenue Analytics",
    subtitle: "Transaction volume, branch revenue, channel distribution, and margins",
    category: "Business Intelligence",
  },
  "/inventory": {
    title: "Inventory & Fulfillment",
    subtitle: "Facility capacities, stockout rates, SKU velocity, and safety thresholds",
    category: "Business Intelligence",
  },
  "/procurement": {
    title: "Procurement & Purchase Orders",
    subtitle: "PO commitment, goods receipts reconciliation, and supplier delivery times",
    category: "Business Intelligence",
  },
  "/suppliers": {
    title: "Supplier Performance",
    subtitle: "Vendor ratings, on-time delivery rates, risk tiers, and annual spend",
    category: "Business Intelligence",
  },
  "/expenses": {
    title: "Operating Expenses (OpEx)",
    subtitle: "Branch cost allocation, budget variances, and overhead trends",
    category: "Business Intelligence",
  },
  "/monitoring": {
    title: "Pipeline Observability & Run Analytics",
    subtitle: "Airflow DAG execution telemetry, task durations, and medallion volume lineage",
    category: "Data Platform",
  },
  "/data-quality": {
    title: "Data Quality & Automated Testing",
    subtitle: "Automated test suites across 12 Silver datasets and gate promotion status",
    category: "Data Platform",
  },
  "/settings": {
    title: "Platform Settings & Configuration",
    subtitle: "System parameters, notification routing, and environment diagnostics",
    category: "System",
  },
};

export const TopNav: React.FC<TopNavProps> = ({
  onToggleSidebar,
  dateRange,
  onDateRangeChange,
}) => {
  const pathname = usePathname();
  const pageInfo = PAGE_TITLES[pathname] || PAGE_TITLES["/"];

  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [notifications, setNotifications] = useState(NOTIFICATIONS_DATA);

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => n.unread).length;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setShowProfile(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-8">
      {/* Left section: Hamburger & Breadcrumbs/Title */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
          aria-label="Toggle navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
            <span>OpsPulse</span>
            <ChevronRight className="h-3 w-3" />
            <span>{pageInfo.category}</span>
            <ChevronRight className="h-3 w-3" />
            <span className="font-semibold text-slate-700">{pageInfo.title}</span>
          </div>
          <h1 className="text-base font-bold text-slate-900 leading-tight">
            {pageInfo.title}
          </h1>
        </div>
      </div>

      {/* Right section: Date Picker, Notifications, User profile */}
      <div className="flex items-center gap-3">
        {/* Date Range Picker */}
        <DateRangePicker selected={dateRange} onChange={onDateRangeChange} />

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none"
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white ring-2 ring-white">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl animate-in fade-in-50 zoom-in-95">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllRead}
                    className="text-[11px] font-medium text-blue-600 hover:text-blue-800"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-72 divide-y divide-slate-100 overflow-y-auto">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      "flex items-start gap-3 p-3 text-xs transition-colors hover:bg-slate-50",
                      n.unread && "bg-blue-50/40"
                    )}
                  >
                    <div
                      className={cn(
                        "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                        n.type === "pipeline"
                          ? "bg-emerald-100 text-emerald-600"
                          : n.type === "quality"
                          ? "bg-blue-100 text-blue-600"
                          : "bg-amber-100 text-amber-600"
                      )}
                    >
                      {n.type === "pipeline" ? (
                        <Activity className="h-3.5 w-3.5" />
                      ) : n.type === "quality" ? (
                        <Shield className="h-3.5 w-3.5" />
                      ) : (
                        <Bell className="h-3.5 w-3.5" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-slate-900">{n.title}</p>
                      <p className="mt-0.5 text-slate-600">{n.message}</p>
                      <span className="mt-1 block text-[10px] text-slate-400">{n.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile UI */}
        <div className="relative" ref={profileRef}>
          <button
            type="button"
            onClick={() => setShowProfile(!showProfile)}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white p-1.5 shadow-sm transition hover:bg-slate-50 focus:outline-none"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white shadow-sm">
              DE
            </div>
            <div className="hidden text-left text-xs md:block">
              <span className="block font-semibold text-slate-800">Lead Data Engineer</span>
              <span className="block text-[10px] text-slate-400">admin@opspulse.internal</span>
            </div>
            <ChevronDown className="hidden h-3.5 w-3.5 text-slate-400 md:block" />
          </button>

          {showProfile && (
            <div className="absolute right-0 z-50 mt-2 w-56 rounded-xl border border-slate-200 bg-white py-1.5 shadow-xl animate-in fade-in-50 zoom-in-95">
              <div className="border-b border-slate-100 px-3 py-2">
                <span className="block text-xs font-bold text-slate-900">Lead Data Engineer</span>
                <span className="block text-[11px] text-slate-400">admin@opspulse.internal</span>
                <div className="mt-1.5 inline-flex items-center gap-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Role: Ops Admin
                </div>
              </div>

              <div className="py-1">
                <button
                  type="button"
                  onClick={() => setShowProfile(false)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                >
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  Operator Profile
                </button>
                <button
                  type="button"
                  onClick={() => setShowProfile(false)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                >
                  <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
                  Airflow 3.4.0 UI
                </button>
              </div>

              <div className="border-t border-slate-100 pt-1">
                <button
                  type="button"
                  onClick={() => setShowProfile(false)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50"
                >
                  <LogOut className="h-3.5 w-3.5 text-rose-500" />
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
