import { useMutation } from "@tanstack/react-query";
import { api, type EngineReportRequest } from "@/lib/api-client";

export function useEngineReport(engineId: string) {
  return useMutation({
    mutationFn: (request: EngineReportRequest) =>
      api.reportEngine(engineId, request),
  });
}
