"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useZones } from "@/hooks/useZones";
import { useSensorData } from "@/hooks/useSensorData";
import { usePredictions } from "@/hooks/usePredictions";
import { useIrrigationEvents } from "@/hooks/useIrrigationEvents";
import SensorChart from "@/components/dashboard/SensorChart";
import PredictionChart from "@/components/dashboard/PredictionChart";
import IrrigationEventLog from "@/components/dashboard/IrrigationEventLog";
import { EditZoneDialog } from "@/components/dashboard/EditZoneDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, Droplets, RefreshCcw, Settings2, Wifi } from "lucide-react";

export default function ZoneDetailPage() {
  const { id } = useParams();
  const zoneId = Array.isArray(id) ? id[0] : id;
  const router = useRouter();
  
  const [isEditOpen, setIsEditOpen] = useState(false);

  const { data: zones, isLoading: zonesLoading } = useZones();
  const { data: sensorData, isLoading: sensorLoading, isError: sensorError, dataUpdatedAt } = useSensorData(zoneId);
  const { data: predictions, isLoading: predLoading, isError: predError } = usePredictions(zoneId);
  const { data: irrigationEvents, isLoading: irrigLoading, isError: irrigError } = useIrrigationEvents(zoneId);

  const zone = zones?.find(z => (z.zone_id ?? z.id) === zoneId);

  const latestReading = sensorData && sensorData.length > 0 ? sensorData[sensorData.length - 1] : null;
  const currentMoisture = latestReading?.moisture;
  const moistureStatus =
    zone && currentMoisture != null
      ? currentMoisture < zone.moisture_min
        ? { label: "Below Min", color: "text-red-600" }
        : currentMoisture > zone.moisture_max
        ? { label: "Above Max", color: "text-amber-600" }
        : { label: "Optimal", color: "text-emerald-600" }
      : { label: "No Data", color: "text-muted-foreground" };

  if (zonesLoading) {
    return (
      <div className="space-y-8 pb-12">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="md:col-span-2 h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!zone) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-24">
        <p className="text-xl font-bold">Zone not found</p>
        <Button onClick={() => router.push("/zones")} variant="link">Back to zones</Button>
      </div>
    );
  }

  const zoneName = zone.zone_name ?? zone.name;
  const moistureMin = zone.moisture_min;
  const moistureMax = zone.moisture_max;

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/zones")}>
            <ChevronLeft size={24} />
          </Button>
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{zoneName}</h2>
            <div className="flex gap-2 mt-1 flex-wrap">
              <Badge variant={(zone.active ?? zone.is_active) ? "default" : "secondary"}>
                {(zone.active ?? zone.is_active) ? "Active" : "Inactive"}
              </Badge>
              <Badge variant="outline">{zone.crop_type}</Badge>
              <Badge variant="outline">{zone.soil_type}</Badge>
              {dataUpdatedAt > 0 && (
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Wifi size={10} className="text-emerald-500" />
                  Live · updates every 10s
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => window.location.reload()}>
            <RefreshCcw size={18} />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setIsEditOpen(true)}>
            <Settings2 size={18} />
          </Button>
          <Button className="gap-2 bg-[#D97757] hover:bg-[#C4673F] text-white">
            <Droplets size={18} />
            Force Irrigation
          </Button>
        </div>
      </div>
      
      {isEditOpen && (
        <EditZoneDialog zone={zone} open={isEditOpen} onOpenChange={setIsEditOpen} />
      )}

      {/* Current reading stats */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        {[
          {
            label: "Current Moisture",
            value: currentMoisture != null ? `${currentMoisture.toFixed(1)}%` : "—",
            sub: moistureStatus.label,
            color: moistureStatus.color,
          },
          {
            label: "Temperature",
            value: latestReading?.temperature != null ? `${latestReading.temperature.toFixed(1)}°C` : "—",
            sub: "Last reading",
            color: "text-muted-foreground",
          },
          {
            label: "Threshold Min",
            value: `${moistureMin}%`,
            sub: "Lower bound",
            color: "text-muted-foreground",
          },
          {
            label: "Threshold Max",
            value: `${moistureMax}%`,
            sub: "Upper bound",
            color: "text-muted-foreground",
          },
        ].map((stat) => (
          <Card key={stat.label} className="border-none shadow-sm">
            <CardContent className="pt-5 pb-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">{stat.label}</p>
              <p className="text-2xl font-bold font-mono mt-1">{stat.value}</p>
              <p className={`text-xs mt-0.5 font-medium ${stat.color}`}>{stat.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Sensor Chart */}
      <Card className="border-none shadow-sm">
        <CardHeader>
          <CardTitle>Soil Moisture & Temperature</CardTitle>
          <CardDescription>
            Sensor readings over the last 24 hours — refreshes every 10s
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SensorChart
            data={sensorData ?? []}
            moistureMin={moistureMin}
            moistureMax={moistureMax}
            isLoading={sensorLoading}
            isError={sensorError}
          />
        </CardContent>
      </Card>

      {/* Prediction Chart + Irrigation Log */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-none shadow-sm">
          <CardHeader>
            <CardTitle>Predicted vs Actual Moisture</CardTitle>
            <CardDescription>ML model predictions compared to real sensor data</CardDescription>
          </CardHeader>
          <CardContent>
            <PredictionChart
              predictions={predictions ?? []}
              actuals={sensorData ?? []}
              isLoading={predLoading}
              isError={predError}
            />
          </CardContent>
        </Card>

        <Card className="border-none shadow-sm">
          <CardHeader>
            <CardTitle>Irrigation Events</CardTitle>
            <CardDescription>Recent irrigation triggers for this zone</CardDescription>
          </CardHeader>
          <CardContent>
            <IrrigationEventLog
              events={irrigationEvents ?? []}
              isLoading={irrigLoading}
              isError={irrigError}
            />
          </CardContent>
        </Card>
      </div>

      {/* Zone metadata */}
      <Card className="border-none shadow-sm">
        <CardHeader>
          <CardTitle className="text-sm">Zone Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {[
              { label: "Zone ID", value: zone.zone_id ?? zone.id },
              { label: "Soil Type", value: zone.soil_type },
              { label: "Crop Type", value: zone.crop_type },
              { label: "Source", value: zone.source ?? "—" },
            ].map((item) => (
              <div key={item.label}>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">{item.label}</p>
                <p className="font-medium mt-0.5">{item.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
