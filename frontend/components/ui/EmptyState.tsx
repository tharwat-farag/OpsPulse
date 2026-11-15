import React from "react";
import { Inbox, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No data available",
  description = "No records match your selected criteria or filters.",
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        <Inbox className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-slate-800">{title}</h3>
      <p className="mt-1.5 max-w-sm text-xs text-slate-500">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-blue-700"
        >
          <RefreshCw className="h-3 w-3" />
          {actionLabel}
        </button>
      )}
    </div>
  );
};

export const LoadingState: React.FC<{ message?: string; className?: string }> = ({
  message = "Loading analytics...",
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-slate-200/80 bg-white p-12 text-center",
        className
      )}
    >
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
      <span className="mt-3 text-xs font-medium text-slate-500">{message}</span>
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  error?: string;
  onRetry?: () => void;
  className?: string;
}> = ({
  title = "Failed to load operational metrics",
  error = "An error occurred while communicating with the data analytics service.",
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-rose-200 bg-rose-50/50 p-8 text-center",
        className
      )}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-100 text-rose-600">
        <AlertCircle className="h-5 w-5" />
      </div>
      <h4 className="mt-3 text-sm font-semibold text-rose-900">{title}</h4>
      <p className="mt-1 max-w-md text-xs text-rose-600">{error}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-rose-700"
        >
          <RefreshCw className="h-3 w-3" />
          Retry Request
        </button>
      )}
    </div>
  );
};
