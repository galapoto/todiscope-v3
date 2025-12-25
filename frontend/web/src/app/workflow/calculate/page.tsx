"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { useEngines } from "@/hooks/use-engines";
import { engineRegistry } from "@/engines/registry";

export default function CalculatePage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("workflow.calculate.title", { defaultValue: "Calculate" })}
        subtitle={t("workflow.calculate.subtitle", { defaultValue: "Run engine calculations" })}
      >
        <CalculateWorkflow />
      </AppShell>
    </AuthGuard>
  );
}

function CalculateWorkflow() {
  const { t } = useTranslation();
  const router = useRouter();
  const params = useSearchParams();
  const datasetVersionId = params.get("dataset_version_id") || "";
  const engineId = params.get("engine_id") || "";
  const enginesQuery = useEngines();
  const enabledEngines = enginesQuery.data ?? [];
  const [selectedEngine, setSelectedEngine] = useState<string>(engineId);
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<{ run_id: string; engine_id: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCalculate = async () => {
    if (!selectedEngine || !datasetVersionId) {
      setError(String(t("workflow.calculate.missingFields", { defaultValue: "Please select an engine and ensure dataset is set" })));
      return;
    }

    setCalculating(true);
    setError(null);

    try {
      const response = await api.runEngine(selectedEngine, {
        dataset_version_id: datasetVersionId,
        started_at: new Date().toISOString(),
        parameters: {},
      });
      const runId = (response as { run_id?: string }).run_id || "";
      setResult({ run_id: runId, engine_id: selectedEngine });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.calculate.failed", { defaultValue: "Calculation failed" })));
    } finally {
      setCalculating(false);
    }
  };

  const handleContinue = () => {
    if (result) {
      const nextUrl = engineId
        ? `/workflow/report?dataset_version_id=${datasetVersionId}&run_id=${result.run_id}&engine_id=${engineId}`
        : `/workflow/report?dataset_version_id=${datasetVersionId}&run_id=${result.run_id}&engine_id=${result.engine_id}`;
      router.push(nextUrl);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("workflow.calculate.title", { defaultValue: "Run Engine Calculation" })}
        </h3>
        {datasetVersionId && (
          <div className="mb-4 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.calculate.datasetId", { defaultValue: "Dataset Version ID" })}:</span>{" "}
              <code className="font-mono text-xs">{datasetVersionId}</code>
            </p>
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
            {error}
          </div>
        )}
        <div className="space-y-4">
          {!engineId && (
            <div>
              <label className="mb-2 block text-sm font-medium text-[var(--ink-2)]">
                {t("workflow.calculate.selectEngine", { defaultValue: "Select Engine" })}
              </label>
              <select
                value={selectedEngine}
                onChange={(e) => setSelectedEngine(e.target.value)}
                className="w-full rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--ink-1)]"
                disabled={calculating}
              >
                <option value="">{t("workflow.calculate.selectEnginePlaceholder", { defaultValue: "Choose an engine..." })}</option>
                {enabledEngines.map((id) => {
                  const engine = engineRegistry[id];
                  return (
                    <option key={id} value={id}>
                      {engine?.display_name || id}
                    </option>
                  );
                })}
              </select>
            </div>
          )}
          {engineId && (
            <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
              <p className="text-sm text-[var(--ink-2)]">
                <span className="font-medium">{t("workflow.calculate.engine", { defaultValue: "Engine" })}:</span>{" "}
                {engineRegistry[engineId]?.display_name || engineId}
              </p>
            </div>
          )}
          <Button variant="primary" onClick={handleCalculate} loading={calculating} disabled={!selectedEngine || !datasetVersionId}>
            {t("workflow.calculate.run", { defaultValue: "Run Calculation" })}
          </Button>
          {result && (
            <>
              <div className="rounded-lg border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 p-3 text-sm text-[var(--accent-success)]">
                <p>
                  {t("workflow.calculate.success", {
                    defaultValue: "Calculation successful! Run ID: {{runId}}",
                    runId: result.run_id,
                  })}
                </p>
              </div>
              <Button variant="primary" onClick={handleContinue}>
                {t("workflow.calculate.continue", { defaultValue: "Continue to Report" })}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

