import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { engineRegistry } from "@/engines/registry";

export function useEngines() {
  return useQuery({
    queryKey: ["engines"],
    queryFn: async () => {
      const enabled = await api.getEnabledEngines();
      const registryIds = Object.keys(engineRegistry);
      const union = Array.from(new Set([...enabled, ...registryIds]));
      return union.sort((a, b) => a.localeCompare(b));
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
