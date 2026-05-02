"use client";
import { Activity, Droplets, HeartPulse, Clock } from "lucide-react";
import StatCard from "@/components/dashboard/StatCard";
import IrrigationEventLog from "@/components/dashboard/IrrigationEventLog";
import { useZones } from "@/hooks/useZones";
import { useRecentIrrigationEvents } from "@/hooks/useIrrigationEvents";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useZonesOverviewChart } from "@/hooks/useZonesOverviewChart";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";

export default function DashboardPage() {
  const { data: zones, isLoading: zonesLoading } = useZones();
  const { data: recentEvents, isLoading: eventsLoading, isError: eventsError } = useRecentIrrigationEvents(15);
  const { data: overviewData, isLoading: overviewLoading } = useZonesOverviewChart();

  const activeZones = zones?.filter(z => z.active ?? z.is_active) ?? [];
  const lastEvent = recentEvents?.[0];
  const lastEventTime = lastEvent
    ? new Date(lastEvent.triggered_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "—";

  const stats = [
    {
      title: "System Health",
      value: "Healthy",
      description: "All services operational",
      icon: HeartPulse,
      className: "text-emerald-600",
    },
    {
      title: "Active Zones",
      value: zonesLoading ? "..." : activeZones.length,
      description: `Out of ${zones?.length ?? 0} total zones`,
      icon: Droplets,
    },
    {
      title: "Irrigation Events",
      value: eventsLoading ? "..." : recentEvents?.length ?? 0,
      description: "In the last 24 hours",
      icon: Activity,
    },
    {
      title: "Last Event",
      value: lastEventTime,
      description: lastEvent ? lastEvent.zone_id : "No events yet",
      icon: Clock,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
        <p className="text-muted-foreground">Welcome to your irrigation control center.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <StatCard key={i} {...stat} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Zone moisture bar chart */}
        <Card className="col-span-4 border-none shadow-sm">
          <CardHeader>
            <CardTitle>Zone Moisture Overview</CardTitle>
            <CardDescription>Latest moisture reading per zone vs thresholds</CardDescription>
          </CardHeader>
          <CardContent>
            {overviewLoading || !overviewData || overviewData.length === 0 ? (
              <div className="h-[220px] flex flex-col items-center justify-center rounded-xl bg-muted/30 border border-dashed border-border">
                <Droplets size={28} className="text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground font-medium">No sensor data available</p>
                <p className="text-xs text-muted-foreground mt-1">Readings will appear once sensors start publishing</p>
              </div>
            ) : (
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overviewData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="zone" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: "hsl(var(--background))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                      formatter={(v: any) => [v != null ? `${Number(v).toFixed(1)}%` : "N/A", "Moisture"]}
                    />
                    <Bar dataKey="moisture" radius={[4, 4, 0, 0]}>
                      {overviewData.map((entry, index) => (
                        <Cell
                          key={index}
                          fill={
                            entry.moisture < entry.min ? "#EF4444"
                            : entry.moisture > entry.max ? "#F59E0B"
                            : "#D97757"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent irrigation events */}
        <Card className="col-span-3 border-none shadow-sm">
          <CardHeader>
            <CardTitle>Recent Events</CardTitle>
            <CardDescription>Latest irrigation triggers across all zones</CardDescription>
          </CardHeader>
          <CardContent>
            <IrrigationEventLog
              events={recentEvents ?? []}
              isLoading={eventsLoading}
              isError={eventsError}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
