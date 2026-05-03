"use client";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Legend,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import type { SensorReading } from "@/types/zone";

interface Props {
  data: SensorReading[];
  label?: string;
  moistureMin?: number;
  moistureMax?: number;
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
          {entry.name}: <span className="font-mono">{entry.value?.toFixed(1)}</span>
          {entry.name.toLowerCase().includes("moisture") ? "%" : "°C"}
        </p>
      ))}
    </div>
  );
};

export default function SensorChart({
  data, label = "Moisture", moistureMin, moistureMax, isLoading, isError,
}: Props) {
  if (isLoading) {
    return <Skeleton className="h-[260px] w-full rounded-xl" />;
  }

  if (isError) {
    return (
      <div className="h-[260px] flex items-center justify-center rounded-xl bg-destructive/5 border border-destructive/20">
        <p className="text-sm text-destructive font-medium">Failed to load sensor data</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-[260px] flex flex-col items-center justify-center rounded-xl bg-muted/30 border border-dashed border-border">
        <p className="text-sm text-muted-foreground font-medium">No sensor readings yet</p>
        <p className="text-xs text-muted-foreground mt-1">Data will appear once sensors start publishing</p>
      </div>
    );
  }

  const chartData = data.map((r) => ({
    time: formatTime(r.timestamp),
    moisture: r.moisture,
    temperature: r.temperature,
  }));

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
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
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
          />

          {moistureMin != null && (
            <ReferenceLine
              y={moistureMin}
              stroke="#EF4444"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{ value: `Min ${moistureMin}%`, position: "insideBottomLeft", fontSize: 9, fill: "#EF4444" }}
            />
          )}
          {moistureMax != null && (
            <ReferenceLine
              y={moistureMax}
              stroke="#10B981"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{ value: `Max ${moistureMax}%`, position: "insideTopLeft", fontSize: 9, fill: "#10B981" }}
            />
          )}

          <Line
            type="monotone"
            dataKey="moisture"
            stroke="#D97757"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            name="Moisture %"
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="temperature"
            stroke="#6B8CFF"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            name="Temp °C"
            strokeDasharray="4 2"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
