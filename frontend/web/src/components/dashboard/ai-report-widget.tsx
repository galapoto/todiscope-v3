"use client";

import { useTranslation } from "react-i18next";
import { AIPanel } from "@/components/ai/ai-panel";
import { api } from "@/lib/api-client";
import { useDatasetContext } from "@/components/data/dataset-context";
import { useQuery } from "@tanstack/react-query";
import { useEngineResults } from "@/components/engines/engine-results-context";
import { getOpenAIKey, hasOpenAIKey } from "@/lib/openai-storage";

export function AIReportWidget() {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();
  const { getAllForDataset } = useEngineResults();
  const aiProbe = useQuery({
    queryKey: ["capability-ai"],
    staleTime: 60_000,
    retry: false,
    queryFn: () => api.probeEndpoint("/api/v3/ai/query"),
  });

  const aiSupported = Boolean(aiProbe.data?.exists);
  const datasetHasResults = Boolean(datasetVersionId && getAllForDataset(datasetVersionId).length);
  const openaiKey = getOpenAIKey();
  const hasKey = hasOpenAIKey();

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex-1">
        {!datasetVersionId ? (
          <div className="flex h-full items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-center text-sm text-[var(--ink-3)]">
            {t("reports.selectDataset", {
              defaultValue: "Select a dataset to enable AI context.",
            })}
          </div>
        ) : !hasKey ? (
          <div className="flex h-full items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-center text-sm text-[var(--ink-3)]">
            {t("reports.aiUnavailable", {
              defaultValue:
                "AI insights require an OpenAI API key. Configure it in Settings.",
            })}
          </div>
        ) : !aiSupported ? (
          <div className="flex h-full items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-center text-sm text-[var(--ink-3)]">
            {t("reports.aiUnavailable", {
              defaultValue:
                "AI insights are unavailable because the backend AI endpoint is not enabled.",
            })}
          </div>
        ) : !datasetHasResults ? (
          <div className="flex h-full items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-center text-sm text-[var(--ink-3)]">
            {t("reports.aiNoResults", {
              defaultValue: "Run an engine or generate a report to seed AI insights.",
            })}
          </div>
        ) : (
          <AIPanel
            context={{
              dataset: datasetVersionId || undefined,
            }}
            onQuery={async (queryText, context) => {
              return await api.queryAI(queryText, context, openaiKey || undefined);
            }}
          />
        )}
      </div>
    </div>
  );
}
