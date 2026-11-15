"use client";

import React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchFilterProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export const SearchFilter: React.FC<SearchFilterProps> = ({
  value,
  onChange,
  placeholder = "Search records...",
  className,
}) => {
  return (
    <div className={cn("relative flex items-center", className)}>
      <Search className="absolute left-3 h-3.5 w-3.5 text-slate-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-8 text-xs text-slate-800 placeholder-slate-400 shadow-sm transition-all focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2.5 rounded-full p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </div>
  );
};
