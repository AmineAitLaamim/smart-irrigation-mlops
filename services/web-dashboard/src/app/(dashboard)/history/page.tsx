"use client";

import { useState } from "react";
import { useZones } from "@/hooks/useZones";
import { useRecentIrrigationEvents } from "@/hooks/useIrrigationEvents";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Droplets, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

export default function HistoryPage() {
  const { data: zones } = useZones();
  const { data: events, isLoading } = useRecentIrrigationEvents(100);
  
  const [selectedZone, setSelectedZone] = useState<string>("all");

  const filteredEvents = events?.filter(event => {
    if (selectedZone !== "all" && event.zone_id !== selectedZone) {
      return false;
    }
    return true;
  }) ?? [];

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 gap-1"><CheckCircle2 size={12}/> Completed</Badge>;
      case "failed":
        return <Badge variant="destructive" className="gap-1"><AlertTriangle size={12}/> Failed</Badge>;
      case "triggered":
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200 gap-1"><Droplets size={12}/> Triggered</Badge>;
      default:
        return <Badge variant="secondary" className="gap-1"><Loader2 className="animate-spin" size={12}/> Pending</Badge>;
    }
  };

  const getZoneName = (zoneId: string) => {
    const zone = zones?.find(z => (z.zone_id ?? z.id) === zoneId);
    return zone ? (zone.zone_name ?? zone.name) : zoneId;
  };

  const formatReason = (reason: string) => reason.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Irrigation History</h2>
        <p className="text-muted-foreground">View past irrigation events and triggers across all zones.</p>
      </div>

      <div className="flex gap-4 items-center">
        <div className="w-[200px]">
          <Select value={selectedZone} onValueChange={(val) => setSelectedZone(val || "all")}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by zone" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Zones</SelectItem>
              {zones?.map(zone => (
                <SelectItem key={zone.zone_id ?? zone.id} value={zone.zone_id ?? zone.id}>
                  {zone.zone_name ?? zone.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-sm text-muted-foreground">
          Showing {filteredEvents.length} events
        </p>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date & Time</TableHead>
              <TableHead>Zone</TableHead>
              <TableHead>Trigger Reason</TableHead>
              <TableHead>Volume (L)</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                  <TableCell><Skeleton className="h-6 w-20 rounded-full" /></TableCell>
                </TableRow>
              ))
            ) : filteredEvents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  No irrigation events found.
                </TableCell>
              </TableRow>
            ) : (
              filteredEvents.map((event, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">
                    {new Date(event.triggered_at).toLocaleString()}
                  </TableCell>
                  <TableCell>{getZoneName(event.zone_id)}</TableCell>
                  <TableCell>{formatReason(event.trigger_reason)}</TableCell>
                  <TableCell>{event.recommended_volume?.toFixed(1) ?? "—"}</TableCell>
                  <TableCell>{getStatusBadge(event.status)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
