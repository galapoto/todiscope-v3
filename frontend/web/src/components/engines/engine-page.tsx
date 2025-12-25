"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { useDatasetContext } from "@/components/data/dataset-context";
import { api } from "@/lib/api-client";
import { getEngineDefinition, engineRegistry } from "@/engines/registry";
import { useEngineResults } from "@/components/engines/engine-results-context";
import { EmptyState } from "@/components/system/empty-state";
import { ReportDashboard } from "@/components/reports/report-dashboard";
import {
  Upload,
  ArrowRight,
  Calculator,
  FileText,
  Shield,
  CheckCircle2,
  Circle,
  AlertCircle,
} from "lucide-react";

// Engine classification for report behavior enforcement
const ENGINE_CLASSES = {
  CLASS_A: [
    "engine_csrd",
    "engine_financial_forensics",
    "engine_construction_cost_intelligence",
    "engine_enterprise_capital_debt_readiness",
    "engine_enterprise_insurance_claim_forensics",
    "engine_enterprise_litigation_dispute",
    "engine_distressed_asset_debt_stress",
  ],
  CLASS_B: [
    "engine_audit_readiness",
    "engine_data_migration_readiness",
    "engine_regulatory_readiness",
  ],
  CLASS_C: [
    "engine_erp_integration_readiness",
  ],
} as const;

function isClassA(engineId: string): boolean {
  return ENGINE_CLASSES.CLASS_A.includes(engineId as any);
}

function extractEvidenceIds(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const any = payload as Record<string, unknown>;
  const maybe = any.evidence_ids;
  if (Array.isArray(maybe)) {
    return maybe.filter((v): v is string => typeof v === "string");
  }
  return [];
}

export function EnginePage({ engineId }: { engineId: string }) {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();
  const { results, record } = useEngineResults();
  const [runError, setRunError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [reporting, setReporting] = useState(false);
  const isRegistered = Boolean(engineRegistry[engineId]);

  const engine = useMemo(() => {
    const def = getEngineDefinition(engineId);
    // Log if engine not found in registry (for debugging)
    if (!engineRegistry[engineId]) {
      console.error(`Engine "${engineId}" not found in registry. Engine page cannot render.`);
    }
    return def;
  }, [engineId]);

  const capabilityProbe = useQuery({
    queryKey: ["engine-probe", engineId],
    staleTime: 60_000,
    retry: false,
    refetchOnMount: false, // Don't refetch on mount if data exists
    refetchOnWindowFocus: false, // Don't refetch on window focus
    queryFn: async () => {
      const [run, report] = await Promise.all([
        api.probeEngineEndpoint(engineId, "run"),
        api.probeEngineEndpoint(engineId, "report"),
      ]);
      return { run, report };
    },
  });

  // Check lifecycle stage completion via workflow state
  const lifecycleState = useQuery({
    queryKey: ["lifecycle-state", datasetVersionId, engineId],
    staleTime: 30_000,
    retry: false,
    enabled: Boolean(datasetVersionId),
    queryFn: async () => {
      if (!datasetVersionId) return null;
      const [importState, normalizeState, calculateState] = await Promise.all([
        api.getWorkflowState(datasetVersionId, "lifecycle", "import").catch(() => null),
        api.getWorkflowState(datasetVersionId, "lifecycle", "normalize").catch(() => null),
        api
          .getWorkflowState(datasetVersionId, "lifecycle", `calculate:${engineId}`)
          .catch(() => null),
      ]);
      return {
        import: importState?.current_state === "approved" || false,
        normalize: normalizeState?.current_state === "approved" || false,
        calculate: calculateState?.current_state === "approved" || false,
      };
    },
  });

  const latestRun = useMemo(() => {
    if (!datasetVersionId) return null;
    return (
      results.find(
        (r) =>
          r.engineId === engineId && r.datasetVersionId === datasetVersionId && r.kind === "run"
      ) ?? null
    );
  }, [datasetVersionId, engineId, results]);

  const latestReport = useMemo(() => {
    if (!datasetVersionId) return null;
    return (
      results.find(
        (r) =>
          r.engineId === engineId && r.datasetVersionId === datasetVersionId && r.kind === "report"
      ) ?? null
    );
  }, [datasetVersionId, engineId, results]);

  const runSupported = capabilityProbe.data?.run.exists ?? false;
  const reportSupported = capabilityProbe.data?.report.exists ?? false;

  const canRun = Boolean(datasetVersionId && runSupported && !running);
  const canReport = Boolean(datasetVersionId && reportSupported && !reporting);

  const evidenceIds = [
    ...extractEvidenceIds(latestRun?.payload),
    ...extractEvidenceIds(latestReport?.payload),
  ].slice(0, 8);

  const reportPayload = useMemo(() => {
    if (!latestReport?.payload || typeof latestReport.payload !== "object") return null;
    const payload = latestReport.payload as Record<string, unknown>;
    return "report" in payload ? payload.report : payload;
  }, [latestReport]);

  const router = useRouter();

  // Determine lifecycle stage status
  const lifecycleStages = useMemo(() => {
    const runId = latestRun?.payload && typeof latestRun.payload === "object" && "run_id" in latestRun.payload
      ? String((latestRun.payload as { run_id?: unknown }).run_id || "")
      : "";
    
    const importCompleted = lifecycleState.data?.import ?? false;
    const normalizeCompleted = lifecycleState.data?.normalize ?? false;
    const calculateCompleted = lifecycleState.data?.calculate ?? false;
    
    const stages = [
      {
        id: "import",
        label: t("workflow.import.title", { defaultValue: "Import" }),
        icon: Upload,
        path: `/workflow/import?engine_id=${engineId}`,
        status: importCompleted ? "completed" : datasetVersionId ? "available" : "pending",
        description: t("workflow.import.subtitle", { defaultValue: "Upload and ingest datasets" }),
        blockedReason: !datasetVersionId
          ? t("workflow.import.blocked", {
              defaultValue: "No dataset version selected. Import a dataset first.",
            })
          : undefined,
      },
      {
        id: "normalize",
        label: t("workflow.normalize.title", { defaultValue: "Normalize" }),
        icon: ArrowRight,
        path: datasetVersionId ? `/workflow/normalize?dataset_version_id=${datasetVersionId}&engine_id=${engineId}` : null,
        status: normalizeCompleted
          ? "completed"
          : importCompleted
            ? "available"
            : datasetVersionId
              ? "blocked"
              : "blocked",
        description: t("workflow.normalize.subtitle", { defaultValue: "Normalize and validate dataset" }),
        blockedReason: !datasetVersionId
          ? t("workflow.normalize.blockedNoDataset", {
              defaultValue: "No dataset version selected.",
            })
          : !importCompleted
            ? t("workflow.normalize.blockedNoImport", {
                defaultValue: "Import must be completed before normalization.",
              })
            : undefined,
      },
      {
        id: "calculate",
        label: t("workflow.calculate.title", { defaultValue: "Calculate" }),
        icon: Calculator,
        path:
          datasetVersionId && runSupported && normalizeCompleted
            ? `/workflow/calculate?dataset_version_id=${datasetVersionId}&engine_id=${engineId}`
            : null,
        status: calculateCompleted || latestRun
          ? "completed"
          : normalizeCompleted && runSupported
            ? "available"
            : "blocked",
        description: t("workflow.calculate.subtitle", { defaultValue: "Run engine calculations" }),
        blockedReason: !datasetVersionId
          ? t("workflow.calculate.blockedNoDataset", {
              defaultValue: "No dataset version selected.",
            })
          : !normalizeCompleted
            ? t("workflow.calculate.blockedNoNormalize", {
                defaultValue: "Normalization must be completed before calculation.",
              })
          : !runSupported
            ? t("coverage.notes.noRunEndpoint", {
                defaultValue: "No engine run endpoint detected for this engine.",
              })
            : undefined,
      },
      // Report stage - ONLY for Class A engines (report-producing engines)
      ...(isClassA(engineId)
        ? [
            {
              id: "report",
              label: t("workflow.report.title", { defaultValue: "Report" }),
              icon: FileText,
              path:
                datasetVersionId && runId && reportSupported && calculateCompleted
                  ? `/workflow/report?dataset_version_id=${datasetVersionId}&run_id=${runId}&engine_id=${engineId}`
                  : null,
              status:
                !reportSupported
                  ? "blocked"
                  : latestReport
                    ? "completed"
                    : calculateCompleted || latestRun
                      ? "available"
                      : "blocked",
              description: t("workflow.report.subtitle", { defaultValue: "Generate compliance report" }),
              blockedReason: !reportSupported
                ? t("coverage.notes.noReportEndpoint", {
                    defaultValue: "No engine report endpoint detected for this engine.",
                  })
                : !datasetVersionId
                  ? t("workflow.report.blockedNoDataset", {
                      defaultValue: "No dataset version selected.",
                    })
              : !calculateCompleted && !latestRun
                ? t("workflow.report.blockedNoCalculate", {
                    defaultValue: "Calculation must be completed before report generation.",
                  })
                : undefined,
            },
          ]
        : []),
      {
        id: "audit",
        label: t("workflow.audit.title", { defaultValue: "Audit" }),
        icon: Shield,
        path: datasetVersionId ? `/audit?dataset_version_id=${datasetVersionId}&engine_id=${engineId}` : null,
        status: datasetVersionId ? "available" : "blocked",
        description: t("workflow.audit.subtitle", { defaultValue: "View audit trail and compliance logs" }),
        blockedReason: !datasetVersionId
          ? t("workflow.audit.blocked", {
              defaultValue: "No dataset version selected.",
            })
          : undefined,
      },
    ];
    return stages;
  }, [
    datasetVersionId,
    engineId,
    latestRun,
    latestReport,
    reportSupported,
    runSupported,
    lifecycleState.data,
    t,
  ]);

  if (!isRegistered) {
    return (
      <AppShell
        title={t("engine.missing.title", { defaultValue: "Engine unavailable" })}
        subtitle={t("engine.label", { defaultValue: "Engine" })}
      >
        <EmptyState
          title={t("engine.missing", { defaultValue: "Engine not registered" })}
          description={t("engine.missingDetail", {
            defaultValue:
              "This engine is not present in the frontend registry. Check engine IDs and reload.",
          })}
          actionLabel={t("engine.back", { defaultValue: "Back to dashboard" })}
          onAction={() => router.push("/dashboard")}
        />
      </AppShell>
    );
  }

  return (
    <AppShell
      title={engine.display_name}
      subtitle={t("engine.label", { defaultValue: "Engine" })}
    >
      <div className="grid gap-6">
        {/* Engine Overview */}
        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">{engine.engine_id}</p>
              <h2 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">{engine.display_name}</h2>
              <p className="mt-2 text-sm text-[var(--ink-3)]">
                {engine.description ||
                  "This engine consumes an imported dataset version, runs deterministic checks/calculations, and produces results with traceable evidence IDs when available."}
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--ink-3)]">
                {engine.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-2)]">
              <p className="font-semibold text-[var(--ink-1)]">Inputs & outputs</p>
              <dl className="mt-3 space-y-2">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">Consumes</dt>
                  <dd className="mt-1">
                    {datasetVersionId ? (
                      <span className="font-mono text-xs">{datasetVersionId}</span>
                    ) : (
                      <span className="text-[var(--ink-3)]">No dataset selected</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">Produces</dt>
                  <dd className="mt-1 text-[var(--ink-3)]">
                    {runSupported ? t("engine.produces.runResults", { defaultValue: "Run results" }) : t("engine.produces.noRunEndpoint", { defaultValue: "No run endpoint" })}
                    {isClassA(engineId) && reportSupported ? `, ${t("engine.produces.reportOutput", { defaultValue: "report output" })}` : ""}
                    {evidenceIds.length ? `, ${t("engine.produces.evidenceLinks", { count: evidenceIds.length, defaultValue: "{{count}} evidence link(s)" })}` : ""}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        {/* Engine Lifecycle Navigation */}
        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-[var(--ink-1)]">
              {t("engine.lifecycle.title", { defaultValue: "Engine Lifecycle" })}
            </h2>
            <p className="mt-1 text-sm text-[var(--ink-3)]">
              {t("engine.lifecycle.subtitle", {
                defaultValue: "Complete the workflow stages to process data and generate reports.",
              })}
            </p>
          </div>

          <div className="space-y-3">
            {lifecycleStages.map((stage, index) => {
              const Icon = stage.icon;
              const isClickable = stage.path !== null;
              const statusIcon =
                stage.status === "completed" ? (
                  <CheckCircle2 className="h-5 w-5 text-[var(--accent-success)]" />
                ) : stage.status === "blocked" ? (
                  <Circle className="h-5 w-5 text-[var(--ink-3)] opacity-50" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-[var(--accent-warning)]" />
                );

              const baseColorClass =
                index % 2 === 0
                  ? "border-green-500/30 bg-green-500/10"
                  : "border-blue-500/30 bg-blue-500/10";

              return (
                <div
                  key={stage.id}
                  className={`flex items-center gap-4 rounded-xl border p-4 transition ${
                    stage.status === "completed"
                      ? "border-[var(--accent-success)]/40 bg-[var(--accent-success)]/5"
                      : stage.status === "blocked"
                        ? `${baseColorClass} opacity-60`
                        : `${baseColorClass} hover:opacity-80`
                  }`}
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--surface-1)]">
                    <Icon className="h-5 w-5 text-[var(--ink-2)]" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-[var(--ink-1)]">{stage.label}</h3>
                      {statusIcon}
                    </div>
                    <p className="mt-1 text-xs text-[var(--ink-3)]">{stage.description}</p>
                    {"blockedReason" in stage && stage.blockedReason ? (
                      <p className="mt-1 text-xs text-[var(--ink-3)]">{stage.blockedReason}</p>
                    ) : null}
                  </div>
                  {isClickable ? (
                    <Button
                      variant={stage.status === "completed" ? "secondary" : "primary"}
                      size="sm"
                      onClick={() => {
                        if (stage.path) router.push(stage.path);
                      }}
                    >
                      {stage.status === "completed"
                        ? t("engine.lifecycle.view", { defaultValue: "View" })
                        : t("engine.lifecycle.start", { defaultValue: "Start" })}
                    </Button>
                  ) : (
                    <Button variant="ghost" size="sm" disabled>
                      {t("engine.lifecycle.blocked", { defaultValue: "Blocked" })}
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Report Dashboard - ONLY for Class A engines */}
        {isClassA(engineId) && reportPayload ? (
          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                  {t("reports.dashboard.title", { defaultValue: "Report dashboard" })}
                </p>
                <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
                  {t("reports.dashboard.subtitle", {
                    defaultValue: "Charts and distribution views generated from the latest report.",
                  })}
                </h3>
              </div>
              <Link
                href="/reports"
                className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-xs font-semibold text-[var(--ink-2)]"
              >
                {t("reports.dashboard.link", { defaultValue: "Open reports workspace" })}
              </Link>
            </div>
            <div className="mt-6">
              <ReportDashboard report={reportPayload} />
            </div>
          </section>
        ) : null}

        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-[240px] flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {engine.engine_id}
              </p>
              <p className="mt-2 text-sm text-[var(--ink-3)]">
                {t("datasets.label", { defaultValue: "Dataset" })}:{" "}
                <span className="font-semibold text-[var(--ink-2)]">
                  {datasetVersionId ? datasetVersionId.slice(0, 12) : "—"}
                </span>
              </p>
              {!datasetVersionId ? (
                <div className="mt-4">
                  <EmptyState
                    title={t("reports.selectDataset", {
                      defaultValue: "Select a dataset version to enable report generation.",
                    })}
                    description={t("datasets.empty", {
                      defaultValue:
                        "No dataset has been imported yet. Import a dataset to unlock engines and reports.",
                    })}
                  />
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                disabled={!canRun}
                loading={running}
                onClick={async () => {
                  if (!datasetVersionId) return;
                  setRunError(null);
                  setRunning(true);
                  try {
                    const payload = await api.runEngine(engineId, {
                      dataset_version_id: datasetVersionId,
                      started_at: new Date().toISOString(),
                      parameters: {},
                    });
                    record({ engineId, datasetVersionId, kind: "run", payload });
                  } catch (error) {
                    const message = error instanceof Error ? error.message : "";
                    setRunError(message || t("states.error", { defaultValue: "Error" }));
                  } finally {
                    setRunning(false);
                  }
                }}
              >
                {t("engine.run", { defaultValue: "Run" })}
              </Button>
              {/* Report button - ONLY for Class A engines */}
              {isClassA(engineId) && (
                <>
                  <Button
                    variant="secondary"
                    disabled={!canReport}
                    loading={reporting}
                    onClick={async () => {
                      if (!datasetVersionId) return;
                      setReportError(null);
                      setReporting(true);
                      try {
                        const payload = await api.reportEngine(engineId, {
                          dataset_version_id: datasetVersionId,
                          report_type: "standard",
                          view_type: "internal",
                          parameters: {},
                        });
                        record({ engineId, datasetVersionId, kind: "report", payload });
                      } catch (error) {
                        const message = error instanceof Error ? error.message : "";
                        setReportError(message || t("states.error", { defaultValue: "Error" }));
                      } finally {
                        setReporting(false);
                      }
                    }}
                  >
                    {t("engine.report", { defaultValue: "Report" })}
                  </Button>
                  <Link
                    href="/reports"
                    className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-sm font-semibold text-[var(--ink-2)]"
                  >
                    {t("dashboard.goToReports", { defaultValue: "Go to reports" })}
                  </Link>
                </>
              )}
            </div>
          </div>

          {capabilityProbe.isLoading ? (
            <p className="mt-4 text-sm text-[var(--ink-3)]">{t("states.loading")}</p>
          ) : (
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--ink-3)]">
              <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
                {t("coverage.capabilities.data", { defaultValue: "Data" })}:{" "}
                {runSupported ? "✅" : "—"}
              </span>
              {/* Reports capability - ONLY show for Class A engines */}
              {isClassA(engineId) && (
                <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
                  {t("coverage.capabilities.reports", { defaultValue: "Reports" })}:{" "}
                  {reportSupported ? "✅" : "—"}
                </span>
              )}
            </div>
          )}

          {runError ? (
            <div className="mt-4 rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
              {runError}
            </div>
          ) : null}
          {reportError ? (
            <div className="mt-4 rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
              {reportError}
            </div>
          ) : null}
        </section>

        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("dashboard.metricDetail", { defaultValue: "Metric detail" })}
              </p>
              <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
                {t("coverage.capabilities.evidence", { defaultValue: "Evidence" })}
              </h3>
            </div>
          </div>

          {!datasetVersionId ? (
            <p className="mt-4 text-sm text-[var(--ink-3)]">
              {t("reports.selectDataset", {
                defaultValue: "Select a dataset version to enable report generation.",
              })}
            </p>
          ) : evidenceIds.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {evidenceIds.map((id) => (
                <Link
                  key={id}
                  href={`/evidence/${id}`}
                  className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1 text-sm font-semibold text-[var(--ink-2)] hover:bg-[var(--surface-3)]"
                >
                  {id.slice(0, 12)}
                </Link>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-3)]">
              {t("evidence.none", { defaultValue: "No evidence available." })}
            </div>
          )}
        </section>

        {(latestRun || latestReport) && datasetVersionId ? (
          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                  {t("engine.viewRaw", { defaultValue: "View raw response" })}
                </p>
                <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
                  {t("dashboard.metrics.latestRun", { defaultValue: "Latest run" })}
                </h3>
              </div>
            </div>
            <pre className="mt-4 max-h-[420px] overflow-auto rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-xs text-[var(--ink-2)]">
              {JSON.stringify({ latestRun, latestReport }, null, 2)}
            </pre>
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
