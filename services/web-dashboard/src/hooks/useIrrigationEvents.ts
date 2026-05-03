import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IrrigationEvent } from "@/types/zone";

const pollingInterval = Number(process.env.NEXT_PUBLIC_POLLING_INTERVAL_MS) || 10000;

export function useIrrigationEvents(zoneId: string | undefined, limit = 20) {
  return useQuery({
    queryKey: ["irrigation", zoneId, limit],
    queryFn: () => api.get<IrrigationEvent[]>(`/v1/zones/${zoneId}/irrigation?limit=${limit}`),
    enabled: !!zoneId,
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}

export function useRecentIrrigationEvents(limit = 20) {
  return useQuery({
    queryKey: ["irrigation-recent", limit],
    queryFn: () => api.get<IrrigationEvent[]>(`/v1/irrigation/recent?limit=${limit}`),
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}
