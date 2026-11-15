"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { DateRangeOption } from "@/types";

interface DateRangeContextType {
  dateRange: DateRangeOption;
  setDateRange: (range: DateRangeOption) => void;
  year: number;
  quarter: number | undefined;
}

const DateRangeContext = createContext<DateRangeContextType>({
  dateRange: "fy2025",
  setDateRange: () => {},
  year: 2025,
  quarter: undefined,
});

export const DateRangeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [dateRange, setDateRangeState] = useState<DateRangeOption>("fy2025");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("opspulse_date_range");
      if (saved) {
        setDateRangeState(saved as DateRangeOption);
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  const setDateRange = (range: DateRangeOption) => {
    setDateRangeState(range);
    try {
      localStorage.setItem("opspulse_date_range", range);
    } catch {
      // Ignore localStorage errors
    }
  };

  const year = 2025;
  let quarter: number | undefined = undefined;

  if (dateRange === "q1_2025") {
    quarter = 1;
  } else if (dateRange === "q2_2025") {
    quarter = 2;
  } else if (dateRange === "q3_2025") {
    quarter = 3;
  } else if (dateRange === "q4_2025") {
    quarter = 4;
  }

  return (
    <DateRangeContext.Provider value={{ dateRange, setDateRange, year, quarter }}>
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => useContext(DateRangeContext);
