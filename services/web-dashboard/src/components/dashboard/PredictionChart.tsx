"use client";
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import type { Prediction, SensorReading } from "@/types/zone";

interface Props {
  predictions: Prediction[];
  actuals: SensorReading[];
  isLoading?: boolean;
  isError?: boolean;
}

function formatTime(ts: string) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-background border border-border rounded-xl px-3 py-2 shadow-lg text-xs space-y-1">
      <p className="font-semibold text-foreground">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: <span className="font-mono">{entry.value?.toFixed(1)}%</span>
        </p>
      ))}
    </div>
  );
};

export default function PredictionChart({ predictions, actuals, isLoading, isError }: Props) {
  if (isLoading) {
    return <Skeleton className="h-[260px] w-full rounded-xl" />;
  }

  if (isError) {
    return (
      <div className="h-[260px] flex items-center justify-center rounded-xl bg-destructive/5 border border-destructive/20">
        <p className="text-sm text-destructive font-medium">Failed to load prediction data</p>
      </div>
    );
  }

  if (!predictions || predictions.length === 0) {
    return (
      <div className="h-[260px] flex flex-col items-center justify-center rounded-xl bg-muted/30 border border-dashed border-border">
        <p className="text-sm text-muted-foreground font-medium">No predictions available yet</p>
        <p className="text-xs text-muted-foreground mt-1">Model predictions will appear once the model server is active</p>
      </div>
    );
  }

  // Merge actuals into a lookup by minute for overlay
  const actualMap = new Map<string, number>();
  actuals.forEach((r) => {
    const key = formatTime(r.timestamp);
    if (r.moisture != null) actualMap.set(key, r.moisture);
  });

  const chartData = predictions.map((p) => {
    const time = formatTime(p.predicted_at);
    const halfConf = p.confidence != null ? p.confidence / 2 : 0;
    return {
      time,
      predicted: p.prediction,
      actual: actualMap.get(time) ?? null,
      confLow: p.prediction != null ? p.prediction - halfConf : null,
      confHigh: p.prediction != null ? p.prediction + halfConf : null,
    };
  });

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />

          {/* Confidence interval shading */}
          <Area
            type="monotone"
            dataKey="confHigh"
            fill="#D97757"
            fillOpacity={0.08}
            stroke="none"
            legendType="none"
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="confLow"
            fill="#ffffff"
            fillOpacity={1}
            stroke="none"
            legendType="none"
            connectNulls
          />

          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#D97757"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            name="Predicted %"
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#10B981"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            name="Actual %"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
