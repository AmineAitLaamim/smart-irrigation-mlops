"use client";
import { useZones } from "@/hooks/useZones";
import ZoneCard from "@/components/dashboard/ZoneCard";
import { CreateZoneDialog } from "@/components/dashboard/CreateZoneDialog";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ZonesPage() {
  const { data: zones, isLoading } = useZones();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Zones</h2>
          <p className="text-muted-foreground">Manage your irrigation zones and thresholds.</p>
        </div>
        <CreateZoneDialog />
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-48 rounded-xl bg-secondary animate-pulse" />
            ))
          : zones?.map((zone) => (
              <ZoneCard key={zone.id} zone={zone} />
            ))}
      </div>

      {!isLoading && zones?.length === 0 && (
        <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-border rounded-xl">
          <p className="text-muted-foreground font-medium text-lg">No zones found.</p>
          <Button variant="link" className="mt-2">Create your first zone</Button>
        </div>
      )}
    </div>
  );
}
