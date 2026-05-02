import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Zone } from "@/types/zone";

export function useZones() {
  return useQuery({
    queryKey: ["zones"],
    queryFn: () => api.get<Zone[]>("/v1/zones"),
  });
}
