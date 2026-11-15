import React from "react";
import { ActivityEvent } from "@/types";
import { Activity, ShieldCheck, AlertTriangle, FileText, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActivityFeedProps {
  activities: ActivityEvent[];
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ activities }) => {
  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {activities.map((item, itemIdx) => {
          const isLast = itemIdx === activities.length - 1;
          const Icon =
            item.type === "pipeline"
              ? Activity
              : item.type === "quality"
              ? ShieldCheck
              : item.type === "inventory"
              ? AlertTriangle
              : item.type === "procurement"
              ? FileText
              : TrendingUp;

          return (
            <li key={item.id}>
              <div className="relative pb-8">
                {!isLast && (
                  <span
                    className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-slate-200"
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex items-start space-x-3">
                  <div>
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full ring-8 ring-white",
                        item.severity === "success"
                          ? "bg-emerald-100 text-emerald-600"
                          : item.severity === "warning"
                          ? "bg-amber-100 text-amber-600"
                          : item.severity === "error"
                          ? "bg-rose-100 text-rose-600"
                          : "bg-blue-100 text-blue-600"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="flex justify-between items-center text-xs">
                      <p className="font-semibold text-slate-900">{item.title}</p>
                      <time className="text-[11px] text-slate-400 whitespace-nowrap">
                        {item.timestamp}
                      </time>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-600">{item.description}</p>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
