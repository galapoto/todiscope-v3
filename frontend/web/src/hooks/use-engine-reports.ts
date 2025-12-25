import { useMutation, useQueryClient } from "@tanstack/react-query";
import { defaultEngineAdapter } from "@/engines/adapters";
import type { EngineReportRequest } from "@/lib/api-client";

/**
 * Normalized engine report hook.
 *
 * This wraps generation in a mutation but also stores the last result in the React Query cache
 * so consumers can access it uniformly.
 */
export function useEngineReports(engineId: string) {
  const queryClient = useQueryClient();

  const generate = useMutation({
    mutationFn: (request: EngineReportRequest) =>
      defaultEngineAdapter.report(engineId, request),
    onSuccess: (data, variables) => {
      queryClient.setQueryData([
        "engine",
        engineId,
        "report",
        variables.dataset_version_id,
        variables.run_id ?? null,
        variables.report_type ?? null,
      ], data);
    },
  });

  return { generate };
}

