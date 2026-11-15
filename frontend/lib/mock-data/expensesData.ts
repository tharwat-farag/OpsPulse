/**
 * Demo Mock Data: Operating Expenses Analytics
 */

import { KpiMetric, OperatingExpenseItem } from "@/types";

export const EXPENSES_KPIS: KpiMetric[] = [
  {
    title: "Total Operating Expenses (MTD)",
    value: "$384,650",
    numericValue: 384650,
    changePct: -1.8,
    isPositive: true,
    trend: "down",
    caption: "vs. monthly budget ($395,000)",
    iconName: "Receipt",
  },
  {
    title: "OpEx to Revenue Ratio",
    value: "20.8%",
    numericValue: 20.8,
    changePct: -1.4,
    isPositive: true,
    trend: "down",
    caption: "Target benchmark < 22.0%",
    iconName: "PieChart",
  },
  {
    title: "Budget Variance",
    value: "-$10,350 Favorable",
    numericValue: -10350,
    changePct: -2.6,
    isPositive: true,
    trend: "down",
    caption: "2.6% under allocated budget",
    iconName: "TrendingDown",
  },
  {
    title: "Fleet & Logistics Freight",
    value: "$114,200",
    numericValue: 114200,
    changePct: 2.1,
    isPositive: false,
    trend: "up",
    caption: "29.7% of total expenses",
    iconName: "Truck",
  },
  {
    title: "Warehouse Facility Rent",
    value: "$142,500",
    numericValue: 142500,
    changePct: 0.0,
    isPositive: true,
    trend: "neutral",
    caption: "Fixed leases across 4 sites",
    iconName: "Building",
  },
  {
    title: "Utilities & Maintenance",
    value: "$42,800",
    numericValue: 42800,
    changePct: -5.4,
    isPositive: true,
    trend: "down",
    caption: "Energy efficiency gains",
    iconName: "Zap",
  },
];

export const EXPENSES_BY_CATEGORY = [
  { category: "Facility Leases & Rent", actual: 142500, budget: 142500, share: 37 },
  { category: "Fleet Freight & Fuel", actual: 114200, budget: 110000, share: 30 },
  { category: "Warehouse Personnel Salaries", actual: 58400, budget: 62000, share: 15 },
  { category: "Utilities & Power", actual: 42800, budget: 45000, share: 11 },
  { category: "Packaging Consumables", actual: 16750, budget: 20000, share: 4 },
  { category: "Equipment Maintenance", actual: 10000, budget: 15500, share: 3 },
];

export const EXPENSES_MONTHLY_TREND = [
  { month: "Jun", actual: 368000, budget: 380000 },
  { month: "Jul", actual: 374000, budget: 382000 },
  { month: "Aug", actual: 389000, budget: 385000 },
  { month: "Sep", actual: 379000, budget: 390000 },
  { month: "Oct", actual: 391000, budget: 395000 },
  { month: "Nov (MTD)", actual: 384650, budget: 395000 },
];

export const EXPENSES_TABLE: OperatingExpenseItem[] = [
  {
    expenseId: "EXP-881",
    category: "Facility Leases & Rent",
    branchName: "Central Fulfillment Center",
    period: "Nov 2026",
    actualAmount: 52000.0,
    budgetAmount: 52000.0,
    varianceAmount: 0.0,
    variancePct: 0.0,
  },
  {
    expenseId: "EXP-882",
    category: "Fleet Freight & Fuel",
    branchName: "Westside Flagship",
    period: "Nov 2026",
    actualAmount: 38400.0,
    budgetAmount: 35000.0,
    varianceAmount: 3400.0,
    variancePct: 9.7,
  },
  {
    expenseId: "EXP-883",
    category: "Warehouse Personnel Salaries",
    branchName: "Southern Regional Logistics Hub",
    period: "Nov 2026",
    actualAmount: 22100.0,
    budgetAmount: 24000.0,
    varianceAmount: -1900.0,
    variancePct: -7.9,
  },
  {
    expenseId: "EXP-884",
    category: "Utilities & Power",
    branchName: "Central Fulfillment Center",
    period: "Nov 2026",
    actualAmount: 18400.0,
    budgetAmount: 20000.0,
    varianceAmount: -1600.0,
    variancePct: -8.0,
  },
  {
    expenseId: "EXP-885",
    category: "Equipment Maintenance",
    branchName: "Northeast Rapid Depot",
    period: "Nov 2026",
    actualAmount: 4200.0,
    budgetAmount: 6500.0,
    varianceAmount: -2300.0,
    variancePct: -35.4,
  },
];
