import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Prediction } from "@/types/zone";

const pollingInterval = Number(process.env.NEXT_PUBLIC_POLLING_INTERVAL_MS) || 10000;

export function usePredictions(zoneId: string | undefined, hours = 24) {
  return useQuery({
    queryKey: ["predictions", zoneId, hours],
    queryFn: () => api.get<Prediction[]>(`/v1/zones/${zoneId}/predictions?hours=${hours}`),
    enabled: !!zoneId,
    refetchInterval: pollingInterval,
    staleTime: pollingInterval - 1000,
  });
}
