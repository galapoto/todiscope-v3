import { useMemo } from "react";
import { useEngines } from "@/hooks/use-engines";
import { defaultEngineAdapter } from "@/engines/adapters";
import { getEngineDefinition } from "@/engines/registry";
import type { EngineSummary } from "@/engines/types";

/**
 * Shared engine adapter hook.
 *
 * The returned summary always contains a stable shape, even for unknown engines.
 */
export function useEngine(engineId: string): EngineSummary {
  const { data: enabledEngines = [] } = useEngines();

  return useMemo(() => {
    const enabled = enabledEngines.includes(engineId);
    const def = getEngineDefinition(engineId);
    const base = defaultEngineAdapter.getSummary(engineId);
    return {
      ...base,
      enabled,
      display_name: def.display_name,
      description: def.description,
      capabilities: def.capabilities,
      supported_export_formats: def.supported_export_formats,
    };
  }, [enabledEngines, engineId]);
}

