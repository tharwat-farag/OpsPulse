"use client";

import React, { useState, useRef, useEffect } from "react";
import { Calendar, ChevronDown, Check } from "lucide-react";
import { DateRangeOption } from "@/types";
import { cn } from "@/lib/utils";

interface DateRangePickerProps {
  selected: DateRangeOption;
  onChange: (value: DateRangeOption) => void;
  className?: string;
}

const OPTIONS: { label: string; value: DateRangeOption }[] = [
  { label: "FY 2025 (Full Year)", value: "fy2025" },
  { label: "Q1 2025 (Jan - Mar)", value: "q1_2025" },
  { label: "Q2 2025 (Apr - Jun)", value: "q2_2025" },
  { label: "Q3 2025 (Jul - Sep)", value: "q3_2025" },
  { label: "Q4 2025 (Oct - Dec)", value: "q4_2025" },
  { label: "All Available Data", value: "all" },
];

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  selected,
  onChange,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeOption = OPTIONS.find((o) => o.value === selected) || OPTIONS[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={cn("relative", className)} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
      >
        <Calendar className="h-3.5 w-3.5 text-slate-500" />
        <span>{activeOption.label}</span>
        <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-1.5 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg animate-in fade-in-50 zoom-in-95">
          <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Select Date Range
          </div>
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onChange(opt.value);
                setIsOpen(false);
              }}
              className={cn(
                "flex w-full items-center justify-between px-3 py-1.5 text-left text-xs transition-colors",
                selected === opt.value
                  ? "bg-blue-50 font-medium text-blue-700"
                  : "text-slate-700 hover:bg-slate-50"
              )}
            >
              <span>{opt.label}</span>
              {selected === opt.value && <Check className="h-3.5 w-3.5 text-blue-600" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
