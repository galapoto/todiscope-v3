"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { ReportDashboard } from "@/components/reports/report-dashboard";
import { api } from "@/lib/api-client";

export default function ReportPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("workflow.report.title", { defaultValue: "Generate Report" })}
        subtitle={t("workflow.report.subtitle", { defaultValue: "Generate compliance report" })}
      >
        <ReportWorkflow />
      </AppShell>
    </AuthGuard>
  );
}

function ReportWorkflow() {
  const { t } = useTranslation();
  const router = useRouter();
  const params = useSearchParams();
  const datasetVersionId = params.get("dataset_version_id") || "";
  const runId = params.get("run_id") || "";
  const engineId = params.get("engine_id") || "";

  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  const reportProbe = useQuery({
    queryKey: ["report-probe", engineId],
    enabled: Boolean(engineId),
    staleTime: 60_000,
    retry: false,
    queryFn: async () => api.probeEngineEndpoint(engineId, "report"),
  });
  const reportSupported = reportProbe.data?.exists ?? false;

  const missingRequired = !datasetVersionId || !runId || !engineId;
  const reportBlocked = !missingRequired && !reportSupported;

  const handleGenerate = async () => {
    if (!engineId || !datasetVersionId || !runId) {
      setError(String(t("workflow.report.missingFields", { defaultValue: "Missing required fields" })));
      return;
    }
    if (!reportSupported) {
      setError(
        String(
          t("workflow.report.notSupported", {
            defaultValue: "This engine does not support report generation.",
          })
        )
      );
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const response = await api.reportEngine(engineId, {
        dataset_version_id: datasetVersionId,
        run_id: runId,
        parameters: {},
      });
      setReport(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.report.failed", { defaultValue: "Report generation failed" })));
    } finally {
      setGenerating(false);
    }
  };

  const handleContinue = () => {
    if (datasetVersionId) {
      const nextUrl = engineId
        ? `/workflow/audit?dataset_version_id=${datasetVersionId}&engine_id=${engineId}`
        : `/workflow/audit?dataset_version_id=${datasetVersionId}`;
      router.push(nextUrl);
    }
  };

  return (
    <div className="space-y-6">
      {missingRequired ? (
        <div className="rounded-3xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-6">
          <p className="text-sm text-[var(--accent-error)]">
            {t("workflow.report.missingFields", {
              defaultValue: "Missing required fields. Please complete Calculate stage first.",
            })}
          </p>
        </div>
      ) : reportBlocked ? (
        <div className="rounded-3xl border border-[var(--accent-warning)]/40 bg-[var(--accent-warning)]/10 p-6">
          <p className="text-sm text-[var(--accent-warning)]">
            {t("workflow.report.notSupported", {
              defaultValue: "This engine does not support report generation.",
            })}
          </p>
        </div>
      ) : null}
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("workflow.report.title", { defaultValue: "Generate Report" })}
        </h3>
        <div className="mb-4 space-y-2 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
          {datasetVersionId && (
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.report.datasetId", { defaultValue: "Dataset Version ID" })}:</span>{" "}
              <code className="font-mono text-xs">{datasetVersionId}</code>
            </p>
          )}
          {runId && (
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.report.runId", { defaultValue: "Run ID" })}:</span>{" "}
              <code className="font-mono text-xs">{runId}</code>
            </p>
          )}
          {engineId && (
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.report.engineId", { defaultValue: "Engine" })}:</span> {engineId}
            </p>
          )}
        </div>
        {error && (
          <div className="mb-4 rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
            {error}
          </div>
        )}
        <div className="space-y-4">
          <Button
            variant="primary"
            onClick={handleGenerate}
            loading={generating}
            disabled={missingRequired || reportBlocked || reportProbe.isLoading}
          >
            {t("workflow.report.generate", { defaultValue: "Generate Report" })}
          </Button>
          {report !== null && (
            <>
              <div className="rounded-lg border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 p-3 text-sm text-[var(--accent-success)]">
                <p>{t("workflow.report.success", { defaultValue: "Report generated successfully!" })}</p>
              </div>
              <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
                <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                  {t("workflow.report.dashboard", { defaultValue: "Report Dashboard" })}
                </p>
                <ReportDashboard report={report} />
              </div>
              <details className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
                <summary className="cursor-pointer text-sm font-medium text-[var(--ink-1)]">
                  {t("workflow.report.preview", { defaultValue: "Report Details" })}
                </summary>
                <pre className="mt-3 max-h-96 overflow-auto rounded bg-[var(--surface-1)] p-2 text-xs">
                  {JSON.stringify(report, null, 2)}
                </pre>
              </details>
              <Button variant="primary" onClick={handleContinue}>
                {t("workflow.report.continue", { defaultValue: "Continue to Audit" })}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
