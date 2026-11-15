/**
 * OpsPulse Type System
 * Strongly typed domain entities and API contracts for Retail Operations Intelligence.
 */

export type DateRangeOption =
  | "fy2025"
  | "q1_2025"
  | "q2_2025"
  | "q3_2025"
  | "q4_2025"
  | "all"
  | "today"
  | "7d"
  | "30d"
  | "month"
  | "quarter"
  | "custom";

export interface DateRange {
  label: string;
  value: DateRangeOption;
  startDate?: string;
  endDate?: string;
}

export interface KpiMetric {
  title: string;
  value: string;
  numericValue: number;
  changePct: number;
  isPositive: boolean;
  trend: "up" | "down" | "neutral";
  caption: string;
  iconName: string;
}

export interface RevenueTrendPoint {
  date: string;
  revenue: number;
  target: number;
  cost: number;
}

export interface BranchPerformance {
  branchId: string;
  branchName: string;
  region: string;
  revenue: number;
  orders: number;
  targetAchievementPct: number;
  status: "exceeding" | "on_track" | "underperforming";
}

export interface ChannelShare {
  channel: string;
  revenue: number;
  percentage: number;
  orders: number;
  color: string;
}

export interface ProductPerformance {
  productId: string;
  productName: string;
  sku: string;
  category: string;
  unitsSold: number;
  revenue: number;
  marginPct: number;
  stockStatus: "in_stock" | "low_stock" | "out_of_stock";
}

export interface InventoryItem {
  sku: string;
  productName: string;
  category: string;
  warehouseName: string;
  quantityOnHand: number;
  safetyStock: number;
  reorderPoint: number;
  unitCost: number;
  totalValue: number;
  status: "optimal" | "low_stock" | "out_of_stock" | "overstocked";
}

export interface WarehouseCapacity {
  warehouseId: string;
  warehouseName: string;
  location: string;
  utilizedSqFt: number;
  totalSqFt: number;
  utilizationPct: number;
  skuCount: number;
  totalInventoryValue: number;
}

export interface PurchaseOrder {
  poNumber: string;
  supplierName: string;
  orderDate: string;
  expectedDate: string;
  totalAmount: number;
  lineCount: number;
  status: "draft" | "submitted" | "partially_received" | "received" | "cancelled";
  paymentStatus: "paid" | "pending" | "overdue";
}

export interface SupplierMetric {
  supplierId: string;
  supplierName: string;
  category: string;
  activeContracts: number;
  totalSpendYtd: number;
  onTimeDeliveryPct: number;
  qualityRating: number;
  fulfillmentRatePct: number;
  riskLevel: "low" | "medium" | "high";
}

export interface OperatingExpenseItem {
  expenseId: string;
  category: string;
  branchName: string;
  period: string;
  actualAmount: number;
  budgetAmount: number;
  varianceAmount: number;
  variancePct: number;
}

export interface PipelineRun {
  dagRunId: string;
  dagId: string;
  batchId: string;
  status: "success" | "failed" | "running";
  startTime: string;
  endTime: string;
  durationSeconds: number;
  tasksTotal: number;
  tasksSucceeded: number;
  tasksFailed: number;
}

export interface TaskMetric {
  taskId: string;
  state: "success" | "failed" | "skipped" | "running";
  durationSeconds: number;
  tryNumber: number;
  historicalAvgSeconds: number;
  variancePct: number;
  category: string;
}

export interface DataVolumeLineage {
  layer: "Raw" | "Bronze" | "Silver" | "Quarantine" | "Gold";
  recordCount: number;
  source: string;
}

export interface DataQualitySummary {
  overallScore: number;
  checksExecuted: number;
  checksPassed: number;
  checksFailed: number;
  ruleCategories: {
    category: "Completeness" | "Uniqueness" | "Referential" | "Business Rules" | "Validity";
    passed: number;
    total: number;
  }[];
  datasets: {
    name: string;
    checks: number;
    status: "pass" | "warn" | "fail";
    score: number;
  }[];
}

export interface ActivityEvent {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  type: "pipeline" | "inventory" | "procurement" | "sales" | "quality";
  severity: "info" | "success" | "warning" | "error";
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  type: "alert" | "pipeline" | "stock" | "quality";
}
