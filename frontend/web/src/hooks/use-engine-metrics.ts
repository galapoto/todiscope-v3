import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { EngineMetric } from "@/engines/types";
import { realtime, type RealtimeEvent } from "@/lib/realtime-manager";

/**
 * Engine metrics are primarily fed by the realtime layer.
 * This query acts as a stable cache container + fallback.
 */
export function useEngineMetrics(engineId: string, datasetVersionId: string | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ["engine", engineId, "metrics", datasetVersionId],
    queryFn: async (): Promise<EngineMetric[]> => {
      // Fallback: return whatever is already in cache. Realtime should keep it fresh.
      const existing = queryClient.getQueryData<EngineMetric[]>([
        "engine",
        engineId,
        "metrics",
        datasetVersionId,
      ]);
      return existing ?? [];
    },
    enabled: Boolean(datasetVersionId),
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

export function subscribeEngineMetricUpdates(params: {
  engineId: string;
  datasetVersionId: string;
  onEvent: (metrics: EngineMetric[]) => void;
}) {
  return realtime.subscribe({
    type: "metric_update",
    engine_id: params.engineId,
    dataset_version_id: params.datasetVersionId,
    handler: (event: RealtimeEvent) => {
      params.onEvent(event.payload as EngineMetric[]);
    },
  });
}
