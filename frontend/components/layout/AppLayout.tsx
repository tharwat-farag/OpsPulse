"use client";

import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { DateRangeProvider, useDateRange } from "@/lib/context/DateRangeContext";

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayoutInner: React.FC<AppLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { dateRange, setDateRange } = useDateRange();

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 antialiased">
      {/* Sidebar (fixed on desktop, drawer on mobile) */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopNav
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
        />

        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <DateRangeProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </DateRangeProvider>
  );
};
