import { NotificationItem } from "@/types";

export const NOTIFICATIONS_DATA: NotificationItem[] = [
  {
    id: "notif-1",
    title: "Airflow Pipeline Succeeded",
    message: "DAG opspulse_pipeline executed 30 tasks with 0 errors.",
    time: "15m ago",
    unread: true,
    type: "pipeline",
  },
  {
    id: "notif-2",
    title: "Data Quality Gate Passed",
    message: "100% checks passed across 12 Silver datasets.",
    time: "18m ago",
    unread: true,
    type: "quality",
  },
  {
    id: "notif-3",
    title: "Low Inventory Alert",
    message: "Barcode Scanner 5G (IT-SC-204) reached safety stock.",
    time: "1h ago",
    unread: false,
    type: "stock",
  },
  {
    id: "notif-4",
    title: "PO Received & Verified",
    message: "PO-2026-8840 from EcoPack received at Dallas Hub.",
    time: "3h ago",
    unread: false,
    type: "alert",
  },
];
