"use client";
import { Droplets, Clock, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { IrrigationEvent } from "@/types/zone";

interface Props {
  events: IrrigationEvent[];
  isLoading?: boolean;
  isError?: boolean;
}

function formatRelativeTime(ts: string) {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(ts).toLocaleDateString();
}

function formatReason(reason: string) {
  return reason.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const StatusBadge = ({ status }: { status: string }) => {
  const variants: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
    pending: {
      label: "Pending",
      icon: <Loader2 size={10} className="animate-spin" />,
      className: "bg-amber-100 text-amber-700 border-amber-200",
    },
    triggered: {
      label: "Triggered",
      icon: <Droplets size={10} />,
      className: "bg-blue-100 text-blue-700 border-blue-200",
    },
    completed: {
      label: "Completed",
      icon: <CheckCircle2 size={10} />,
      className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    },
    failed: {
      label: "Failed",
      icon: <AlertTriangle size={10} />,
      className: "bg-red-100 text-red-700 border-red-200",
    },
  };

  const v = variants[status?.toLowerCase()] ?? variants.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${v.className}`}>
      {v.icon}
      {v.label}
    </span>
  );
};

export default function IrrigationEventLog({ events, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-8 rounded-xl bg-destructive/5 border border-destructive/20">
        <p className="text-sm text-destructive font-medium">Failed to load irrigation events</p>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 rounded-xl bg-muted/30 border border-dashed border-border">
        <Droplets size={28} className="text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground font-medium">No irrigation events yet</p>
        <p className="text-xs text-muted-foreground mt-1">Events appear when moisture drops below threshold</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/50 transition-colors"
        >
          <div className="flex-shrink-0 h-8 w-8 rounded-full bg-[#D97757]/10 flex items-center justify-center">
            <Droplets size={14} className="text-[#D97757]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {formatReason(event.trigger_reason)}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <Clock size={10} className="text-muted-foreground flex-shrink-0" />
              <span className="text-xs text-muted-foreground">{formatRelativeTime(event.triggered_at)}</span>
              {event.recommended_volume != null && (
                <>
                  <span className="text-muted-foreground/50">·</span>
                  <span className="text-xs text-muted-foreground font-mono">{event.recommended_volume.toFixed(1)} L</span>
                </>
              )}
              {event.zone_id && (
                <>
                  <span className="text-muted-foreground/50">·</span>
                  <span className="text-xs text-muted-foreground truncate">{event.zone_id}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex-shrink-0">
            <StatusBadge status={event.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
