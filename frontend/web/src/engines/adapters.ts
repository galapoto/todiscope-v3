import { api, type EngineReportRequest, type EngineRunRequest } from "@/lib/api-client";
import type { EngineSummary } from "./types";
import { getEngineDefinition } from "./registry";

export type EngineAdapter = {
  getSummary: (engineId: string) => EngineSummary;
  run: (engineId: string, request: EngineRunRequest) => Promise<unknown>;
  report: (engineId: string, request: EngineReportRequest) => Promise<unknown>;
  status: (engineId: string) => Promise<unknown | null>;
};

export const defaultEngineAdapter: EngineAdapter = {
  getSummary: (engineId) => {
    const def = getEngineDefinition(engineId);
    return {
      engine_id: engineId,
      enabled: true, // final enabled state is resolved in hooks
      display_name: def.display_name,
      description: def.description,
      capabilities: def.capabilities,
      supported_export_formats: def.supported_export_formats,
    };
  },
  run: (engineId, request) => api.runEngine(engineId, request),
  report: (engineId, request) => api.reportEngine(engineId, request),
  status: async (engineId) => {
    const def = getEngineDefinition(engineId);
    if (!def.status_endpoint) return null;
    return api.getEngineStatus(def.status_endpoint);
  },
};

