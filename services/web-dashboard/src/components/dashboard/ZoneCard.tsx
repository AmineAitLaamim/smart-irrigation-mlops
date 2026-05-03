import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Droplets, Settings2, Info } from "lucide-react";
import Link from "next/link";
import type { Zone } from "@/types/zone";
import { EditZoneDialog } from "@/components/dashboard/EditZoneDialog";

interface ZoneCardProps {
  zone: Zone;
}

export default function ZoneCard({ zone }: ZoneCardProps) {
  const [isEditOpen, setIsEditOpen] = useState(false);

  return (
    <>
      <Card className="border-none shadow-sm hover:shadow-md transition-shadow bg-background group">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="space-y-1">
            <CardTitle className="text-xl font-bold tracking-tight">{zone.zone_name ?? zone.name}</CardTitle>
            <div className="flex gap-2">
              <Badge variant={(zone.active ?? zone.is_active) ? "default" : "secondary"}>
                {(zone.active ?? zone.is_active) ? "Active" : "Inactive"}
              </Badge>
              <Badge variant="outline" className="font-mono text-[10px]">
                {zone.soil_type}
              </Badge>
            </div>
          </div>
          <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
            <Droplets size={20} />
          </div>
        </CardHeader>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Moisture Range</p>
              <p className="text-sm font-semibold">{zone.moisture_min}% - {zone.moisture_max}%</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Crop</p>
              <p className="text-sm font-semibold">{zone.crop_type}</p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="pt-2 gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="flex-1"
            render={
              <Link href={`/zones/${zone.zone_id ?? zone.id}`}>
                <Info size={14} className="mr-2" />
                Details
              </Link>
            }
          />
          <Button variant="outline" size="sm" className="px-2" onClick={() => setIsEditOpen(true)}>
            <Settings2 size={14} />
          </Button>
        </CardFooter>
      </Card>
      {isEditOpen && (
        <EditZoneDialog zone={zone} open={isEditOpen} onOpenChange={setIsEditOpen} />
      )}
    </>
  );
}

