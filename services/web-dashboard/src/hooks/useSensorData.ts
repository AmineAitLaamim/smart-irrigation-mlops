import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SensorReading } from "@/types/zone";

const pollingInterval = Number(process.env.NEXT_PUBLIC_POLLING_INTERVAL_MS) || 10000;

export function useSensorData(zoneId: string | undefined, hours = 24) {
  return useQuery({
    queryKey: ["sensors", zoneId, hours],
    queryFn: () => api.get<SensorReading[]>(`/v1/zones/${zoneId}/sensors?hours=${hours}`),
    enabled: !!zoneId,
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}

export function useLatestSensor(zoneId: string | undefined) {
  return useQuery({
    queryKey: ["sensors-latest", zoneId],
    queryFn: () => api.get<SensorReading[]>(`/v1/zones/${zoneId}/sensors/latest`),
    enabled: !!zoneId,
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}
