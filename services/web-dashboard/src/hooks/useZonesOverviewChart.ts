import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useZones } from "@/hooks/useZones";
import type { SensorReading, Zone } from "@/types/zone";

interface ZoneOverviewPoint {
  zone: string;
  moisture: number;
  min: number;
  max: number;
}

async function fetchLatestForZone(zoneId: string): Promise<SensorReading[]> {
  try {
    return await api.get<SensorReading[]>(`/v1/zones/${zoneId}/sensors/latest`);
  } catch {
    return [];
  }
}

export function useZonesOverviewChart() {
  const { data: zones } = useZones();
  const pollingInterval = Number(process.env.NEXT_PUBLIC_POLLING_INTERVAL_MS) || 10000;

  return useQuery({
    queryKey: ["zones-overview-chart", zones?.map(z => z.zone_id ?? z.id)],
    queryFn: async (): Promise<ZoneOverviewPoint[]> => {
      if (!zones || zones.length === 0) return [];

      const results = await Promise.all(
        zones.map(async (zone: Zone) => {
          const zoneId = zone.zone_id ?? zone.id;
          const readings = await fetchLatestForZone(zoneId);
          const moistures = readings.map(r => r.moisture).filter((m): m is number => m != null);
          const avgMoisture = moistures.length > 0
            ? moistures.reduce((a, b) => a + b, 0) / moistures.length
            : null;

          if (avgMoisture == null) return null;

          return {
            zone: zone.zone_name ?? zone.name ?? zoneId,
            moisture: avgMoisture,
            min: zone.moisture_min,
            max: zone.moisture_max,
          };
        })
      );

      return results.filter((r): r is ZoneOverviewPoint => r != null);
    },
    enabled: !!zones && zones.length > 0,
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}
