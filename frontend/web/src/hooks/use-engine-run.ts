import { useMutation } from "@tanstack/react-query";
import { api, type EngineRunRequest } from "@/lib/api-client";

export function useEngineRun(engineId: string) {
  return useMutation({
    mutationFn: (request: EngineRunRequest) => api.runEngine(engineId, request),
  });
}
