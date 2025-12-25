"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { useDatasetContext } from "@/components/data/dataset-context";
import { api } from "@/lib/api-client";
import { useSearch } from "@/components/search/search-context";
import { OCRUpload } from "@/components/ocr/ocr-upload";
import { AIPanel } from "@/components/ai/ai-panel";
import { ExportMenu } from "@/components/export/export-menu";
import { useEngines } from "@/hooks/use-engines";
import { useQuery } from "@tanstack/react-query";
import { getOpenAIKey, hasOpenAIKey } from "@/lib/openai-storage";
import { useEngineResults } from "@/components/engines/engine-results-context";
import { ReportDashboard } from "@/components/reports/report-dashboard";
import { getEngineDefinition } from "@/engines/registry";

const ChartsPanel = dynamic(
  () => import("@/components/dashboard/charts-panel").then((mod) => mod.ChartsPanel),
  { ssr: false }
);
const DatasetTable = dynamic(
  () => import("@/components/data/dataset-table").then((mod) => mod.DatasetTable),
  { ssr: false }
);

export function ReportBuilder() {
  const [scope, setScope] = useState("quarterly");
  const [region, setRegion] = useState("global");
  const [modalOpen, setModalOpen] = useState(false);
  const [engines, setEngines] = useState<string[]>([
    "engine_financial_forensics",
    "engine_csrd",
  ]);
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [exposureLevel, setExposureLevel] = useState("all");
  const { t } = useTranslation();
  const { query } = useSearch();
  const enginesQuery = useEngines();
  const enabledEngines = enginesQuery.data ?? [];
  const openaiKey = hasOpenAIKey() ? getOpenAIKey() : null;
  const hasKey = Boolean(openaiKey);

  const platformProbe = useQuery({
    queryKey: ["platform-capabilities"],
    staleTime: 60_000,
    retry: false,
    queryFn: async () => {
      const [ai, ocr] = await Promise.all([
        api.probeEndpoint("/api/v3/ai/query"),
        api.probeEndpoint("/api/v3/ocr/upload"),
      ]);
      return { ai, ocr };
    },
  });

  const engineCapabilitiesQuery = useQuery({
    queryKey: ["engine-capabilities", enabledEngines],
    enabled: enginesQuery.isSuccess,
    staleTime: 5 * 60 * 1000,
    retry: false,
    queryFn: async () => {
      const entries = await Promise.all(
        enabledEngines.map(async (engineId) => {
          const [run, report] = await Promise.all([
            api.probeEngineEndpoint(engineId, "run"),
            api.probeEngineEndpoint(engineId, "report"),
          ]);
          return [engineId, { run: run.exists, report: report.exists }] as const;
        })
      );
      return Object.fromEntries(entries) as Record<string, { run: boolean; report: boolean }>;
    },
  });

  const engineOptions = useMemo(() => {
    const list = enabledEngines.length ? enabledEngines : engines;
    return list.map((id) => ({
      id,
      label: t(`engines.${id}.name`, { defaultValue: id.replace(/[-_]+/g, " ") }),
    }));
  }, [enabledEngines, engines, t]);
  const filteredEngines = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return engineOptions;
    return engineOptions.filter(
      (engine) =>
        engine.id.toLowerCase().includes(normalizedQuery) ||
        engine.label.toLowerCase().includes(normalizedQuery)
    );
  }, [engineOptions, query]);
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState({
    dataset: false,
    engines: false,
    dateRange: false,
  });
  const [reportError, setReportError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [insights, setInsights] = useState<string[]>([]);
  const { datasetVersionId } = useDatasetContext();
  const { record, getAllForDataset } = useEngineResults();
  const reportResults = useMemo(() => {
    if (!datasetVersionId) return [];
    return getAllForDataset(datasetVersionId).filter((item) => item.kind === "report");
  }, [datasetVersionId, getAllForDataset]);

  const aiSupported = Boolean(platformProbe.data?.ai.exists);
  const ocrSupported = Boolean(platformProbe.data?.ocr.exists);
  const selectedHasReportSupport = engines.some(
    (engineId) => engineCapabilitiesQuery.data?.[engineId]?.report
  );
  const datasetHasResults = Boolean(datasetVersionId && getAllForDataset(datasetVersionId).length);

  return (
    <div className="grid gap-6">
      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("reports.studio")}
              </p>
              <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
                {t("reports.studioTitle")}
              </h3>
            </div>
            <Button
              variant="primary"
              loading={isGenerating}
              data-onboard="report-generate"
              onClick={() => {
                const validationErrors: string[] = [];
                const nextFieldErrors = {
                  dataset: false,
                  engines: false,
                  dateRange: false,
                };
                if (!datasetVersionId) {
                  validationErrors.push(t("reports.validation.dataset"));
                  nextFieldErrors.dataset = true;
                }
                if (!engines.length) {
                  validationErrors.push(t("reports.validation.engines"));
                  nextFieldErrors.engines = true;
                }
                if (!dateStart || !dateEnd) {
                  validationErrors.push(t("reports.validation.dateRange"));
                  nextFieldErrors.dateRange = true;
                }
                if (dateStart && dateEnd && dateStart > dateEnd) {
                  validationErrors.push(t("reports.validation.dateOrder"));
                  nextFieldErrors.dateRange = true;
                }
                setErrors(validationErrors);
                setFieldErrors(nextFieldErrors);
                if (validationErrors.length) return;
                if (enginesQuery.isSuccess && !engineCapabilitiesQuery.data) {
                  setReportError(
                    t("reports.validation.capabilitiesUnavailable", {
                      defaultValue:
                        "Engine capabilities are still loading. Please try again in a moment.",
                    })
                  );
                  return;
                }
                setIsGenerating(true);
                setReportError(null);
                setInsights([]);
                const startedAt = new Date().toISOString();
                const capsByEngine = engineCapabilitiesQuery.data;
                Promise.allSettled(
                  engines.map(async (engineId) => {
                    if (!datasetVersionId) return null;
                    const caps = capsByEngine?.[engineId];
                    if (caps && !caps.run && !caps.report) {
                      return null;
                    }

                    if (caps && !caps.run && caps.report) {
                      throw new Error(
                        t("reports.validation.engineRunMissing", {
                          defaultValue: `Engine ${engineId} does not expose a run endpoint.`,
                        })
                      );
                    }

                    const run = await api.runEngine(engineId, {
                      dataset_version_id: datasetVersionId,
                      started_at: startedAt,
                      parameters: {},
                    });
                    record({
                      engineId,
                      datasetVersionId,
                      kind: "run",
                      payload: run,
                    });

                    if (!caps?.report) {
                      return run;
                    }

                    const runId =
                      typeof run === "object" && run && "run_id" in run
                        ? String((run as { run_id?: string }).run_id || "")
                        : "";
                    if (!runId) {
                      return run;
                    }

                    const report = await api.reportEngine(engineId, {
                      dataset_version_id: datasetVersionId,
                      run_id: runId,
                      parameters: {},
                    });
                    record({
                      engineId,
                      datasetVersionId,
                      kind: "report",
                      payload: report,
                    });
                    return report;
                  })
                )
                  .then((results) => {
                    const nextInsights: string[] = [];
                    const failures = results.filter((result) => result.status === "rejected");

                    results.forEach((result) => {
                      if (result.status !== "fulfilled") return;
                      const response = result.value;
                      if (!response || typeof response !== "object") return;
                      const any = response as Record<string, unknown>;
                      const findingsCount = typeof any.findings_count === "number" ? any.findings_count : null;
                      const evidenceIds = Array.isArray(any.evidence_ids) ? any.evidence_ids : null;
                      if (findingsCount !== null) {
                        nextInsights.push(
                          t("reports.summary.findingsLine", {
                            defaultValue: "Findings detected: {{count}}",
                            count: findingsCount,
                          })
                        );
                      }
                      if (evidenceIds) {
                        nextInsights.push(
                          t("reports.summary.evidenceLine", {
                            defaultValue: "Evidence items linked: {{count}}",
                            count: evidenceIds.length,
                          })
                        );
                      }
                      if (Array.isArray(any.regulatory_results)) {
                        const pending = any.regulatory_results.filter((r) => {
                          if (!r || typeof r !== "object") return false;
                          return (r as Record<string, unknown>).check_status !== "ready";
                        }).length;
                        nextInsights.push(
                          t("reports.summary.auditReadinessLine", {
                            defaultValue: "Regulatory checks pending review: {{count}}",
                            count: pending,
                          })
                        );
                      }
                    });

                    if (!nextInsights.length) {
                      setInsights([
                        t("reports.summary.noInsights", {
                          defaultValue:
                            "Report completed, but no narrative insights were returned. Use the charts and evidence links to explore details.",
                        }),
                      ]);
                    } else {
                      setInsights(nextInsights);
                    }

                    if (failures.length === results.length) {
                      const reason = failures[0]?.reason;
                      const message =
                        reason instanceof Error ? reason.message : String(reason ?? "");
                      setReportError(
                        message.includes("timed out")
                          ? t("reports.validation.reportTimeout")
                          : t("reports.validation.reportFailed")
                      );
                    } else if (failures.length) {
                      setReportError(t("reports.validation.partialFailure"));
                    }
                  })
                  .catch(() => {
                    setReportError(t("reports.validation.reportFailed"));
                  })
                  .finally(() => {
                    setIsGenerating(false);
                  });
              }}
            >
              {t("reports.generate")}
            </Button>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.scope")}
              <select
                value={scope}
                onChange={(event) => setScope(event.target.value)}
                className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)]"
              >
                <option value="quarterly">{t("reports.scopeOptions.quarterly")}</option>
                <option value="monthly">{t("reports.scopeOptions.monthly")}</option>
                <option value="adhoc">{t("reports.scopeOptions.adhoc")}</option>
              </select>
            </label>
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.region")}
              <select
                value={region}
                onChange={(event) => setRegion(event.target.value)}
                className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)]"
              >
                <option value="global">{t("reports.regionOptions.global")}</option>
                <option value="na">{t("reports.regionOptions.na")}</option>
                <option value="emea">{t("reports.regionOptions.emea")}</option>
                <option value="apac">{t("reports.regionOptions.apac")}</option>
              </select>
            </label>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.filters.startDate")}
              <input
                type="date"
                value={dateStart}
                onChange={(event) => setDateStart(event.target.value)}
                className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)]"
                aria-invalid={fieldErrors.dateRange}
              />
            </label>
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.filters.endDate")}
              <input
                type="date"
                value={dateEnd}
                onChange={(event) => setDateEnd(event.target.value)}
                className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)]"
                aria-invalid={fieldErrors.dateRange}
              />
            </label>
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.filters.exposure")}
              <select
                value={exposureLevel}
                onChange={(event) => setExposureLevel(event.target.value)}
                className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)]"
              >
                <option value="all">{t("reports.filters.exposureAll")}</option>
                <option value="high">{t("reports.filters.exposureHigh")}</option>
                <option value="medium">{t("reports.filters.exposureMedium")}</option>
                <option value="low">{t("reports.filters.exposureLow")}</option>
              </select>
            </label>
          </div>
          <div className="mt-4 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.filters.engines")}
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-sm text-[var(--ink-2)]">
              {filteredEngines.length ? (
                filteredEngines.map((engine) => (
                <label key={engine.id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={engines.includes(engine.id)}
                    onChange={(event) => {
                      setEngines((prev) =>
                        event.target.checked
                          ? [...prev, engine.id]
                          : prev.filter((item) => item !== engine.id)
                      );
                    }}
                    aria-invalid={fieldErrors.engines}
                  />
                  {engine.label}
                </label>
              ))
              ) : (
                <p className="text-sm text-[var(--ink-3)]">{t("states.empty")}</p>
              )}
            </div>
          </div>
          {errors.length ? (
            <div className="mt-4 rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
              {errors.map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          ) : reportError ? (
            <div className="mt-4 rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
              <p>{reportError}</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setReportError(null)}
                className="mt-2"
              >
                {t("reports.retry")}
              </Button>
            </div>
          ) : insights.length ? (
            <div className="mt-4 rounded-2xl border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 p-4 text-sm text-[var(--accent-success)]">
              {t("states.success")}
            </div>
          ) : null}
          <div className="mt-5">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.prompt")}
            </p>
            <div className="h-[300px]">
              {aiSupported && selectedHasReportSupport ? (
                <AIPanel
                  context={{
                    engine: engines.join(", "),
                    dataset: datasetVersionId || undefined,
                    report: scope,
                  }}
                  initialInsight={
                    insights.length
                      ? insights.join("\n\n")
                      : t("reports.promptPlaceholder")
                  }
                  onQuery={async (queryText, context) => {
                    if (!hasKey) {
                      throw new Error(
                        t("reports.aiUnavailable", {
                          defaultValue: "OpenAI API key required. Configure it in Settings.",
                        })
                      );
                    }
                    return await api.queryAI(queryText, context, openaiKey || undefined);
                  }}
                />
              ) : (
                <div className="flex h-full items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-center text-sm text-[var(--ink-3)]">
                  {!aiSupported
                    ? t("reports.aiUnavailable", {
                        defaultValue: "AI insights are unavailable because the backend AI endpoint is not enabled.",
                      })
                    : t("reports.aiUnsupportedSelection", {
                        defaultValue:
                          "Select at least one report-capable engine to enable AI insights.",
                      })}
                </div>
              )}
            </div>
          </div>
        </section>
        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {t("reports.ocr.title")}
          </p>
          <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
            {t("reports.ocr.subtitle")}
          </h3>
          <div className="mt-4">
            {ocrSupported ? (
              <OCRUpload
                onUploadComplete={(result) => {
                  console.log("OCR result:", result);
                }}
                onAttachToReport={(result, reportId) => {
                  console.log("Attaching OCR to report:", reportId);
                }}
              />
            ) : (
              <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-3)]">
                {t("reports.ocrUnavailable", {
                  defaultValue: "OCR uploads are unavailable because the backend OCR endpoint is not enabled.",
                })}
              </div>
            )}
          </div>
        </section>
      </div>

      {datasetVersionId ? (
        reportResults.length ? (
          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.dashboard.title", { defaultValue: "Engine Report Dashboards" })}
            </p>
            <div className="mt-4 grid gap-6">
              {reportResults.map((result) => {
                const engine = getEngineDefinition(result.engineId);
                const payload =
                  result.payload && typeof result.payload === "object" && "report" in result.payload
                    ? (result.payload as { report?: unknown }).report
                    : result.payload;
                return (
                  <div
                    key={`${result.engineId}-${result.recordedAt}`}
                    className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-[var(--ink-1)]">{engine.display_name}</h3>
                        <p className="text-sm text-[var(--ink-3)]">
                          {t("reports.dashboard.generatedAt", {
                            defaultValue: "Generated at {{timestamp}}",
                            timestamp: new Date(result.recordedAt).toLocaleString(),
                          })}
                        </p>
                      </div>
                      <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                        {t("reports.dashboard.reportTag", { defaultValue: "Report" })}
                      </span>
                    </div>
                    <div className="mt-4">
                      <ReportDashboard report={payload} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ) : (
          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-3)]">
            {t("reports.dashboard.empty", {
              defaultValue: "No report dashboards yet. Run engines to generate reports and see charts.",
            })}
          </section>
        )
      ) : (
        <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-3)]">
          {t("reports.dashboard.noDataset", {
            defaultValue: "Select a dataset to view report dashboards.",
          })}
        </section>
      )}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("reports.summary.title")}
            </p>
            <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
              {t("reports.summary.subtitlePrefix")} {t(`reports.scopeOptions.${scope}`)}
            </h3>
          </div>
          <div className="flex gap-2">
            <ExportMenu
              data={{
                title: t("reports.pdf.title"),
                content:
                  insights.length > 0
                    ? insights.join("\n\n")
                    : t("reports.empty", { defaultValue: "No report has been run yet." }),
                metadata: {
                  [t("datasets.id")]: datasetVersionId || "--",
                  [t("reports.filters.engines")]: engines.length ? engines.join(", ") : "--",
                  [t("reports.scope")]: t(`reports.scopeOptions.${scope}`),
                  [t("reports.region")]: t(`reports.regionOptions.${region}`),
                  [t("reports.filters.exposure")]: t(
                    exposureLevel === "all"
                      ? "reports.filters.exposureAll"
                      : exposureLevel === "high"
                        ? "reports.filters.exposureHigh"
                        : exposureLevel === "medium"
                          ? "reports.filters.exposureMedium"
                          : "reports.filters.exposureLow"
                  ),
                  [t("reports.filters.startDate")]: dateStart || "--",
                  [t("reports.filters.endDate")]: dateEnd || "--",
                },
              }}
              filename={`report-${scope}-${new Date().toISOString().split("T")[0]}`}
            />
            <Button variant="primary" onClick={() => setModalOpen(true)}>
              {t("reports.summary.share")}
            </Button>
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {(insights.length ? insights : []).map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-2)]"
            >
              {item}
            </div>
          ))}
        </div>
        {!insights.length ? (
          <div className="mt-5 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-3)]">
            {t("reports.empty", { defaultValue: "No report has been run yet." })}
          </div>
        ) : null}
      </section>
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
          {t("reports.visuals.title")}
        </p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
            {t("reports.visuals.subtitle")}
          </h3>
          <Button
            variant="secondary"
            size="sm"
            onClick={async () => {
              try {
                if (!datasetVersionId) throw new Error("missing dataset");
                const XLSX = await import("xlsx");
                const workbook = XLSX.utils.book_new();
                const results = getAllForDataset(datasetVersionId);
                const summarySheet = XLSX.utils.json_to_sheet(
                  results.map((r) => ({
                    engine_id: r.engineId,
                    kind: r.kind,
                    recorded_at: r.recordedAt,
                  }))
                );
                XLSX.utils.book_append_sheet(workbook, summarySheet, "Runs");
                XLSX.writeFile(workbook, "todiscope-charts.xlsx");
              } catch {
                setModalOpen(true);
              }
            }}
            disabled={!datasetHasResults}
          >
            {t("reports.exportExcel")}
          </Button>
        </div>
        <div className="mt-4">
          <ChartsPanel />
        </div>
      </section>
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("datasets.label")}
            </p>
            <h3 className="mt-2 text-xl font-semibold text-[var(--ink-1)]">
              {t("datasets.title")}
            </h3>
          </div>
        </div>
        <div className="mt-4">
          <DatasetTable />
        </div>
      </section>
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={t("reports.shareTitle")}
        size="md"
      >
        <p className="text-sm text-[var(--ink-2)]">{t("reports.shareBody")}</p>
      </Modal>
    </div>
  );
}
