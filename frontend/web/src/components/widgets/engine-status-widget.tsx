"use client";

import { useMemo, useState } from "react";
import { useEngines } from "@/hooks/use-engines";
import { useDatasetContext } from "@/components/data/dataset-context";
import { useEngineRun } from "@/hooks/use-engine-run";
import { useEngineReport } from "@/hooks/use-engine-report";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { useSearch } from "@/components/search/search-context";
import { useEngine } from "@/hooks/use-engine";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import Link from "next/link";
import { useEngineResults, type EngineResultKind } from "@/components/engines/engine-results-context";

function useEngineEndpoints(engineId: string) {
  return useQuery({
    queryKey: ["engine-endpoints", engineId],
    staleTime: 5 * 60 * 1000,
    retry: false,
    queryFn: async () => {
      const [run, report] = await Promise.all([
        api.probeEngineEndpoint(engineId, "run"),
        api.probeEngineEndpoint(engineId, "report"),
      ]);
      return { run, report };
    },
  });
}

export function EngineStatusWidget() {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();
  const { data: engines = [], isLoading, isError } = useEngines();
  const engineResults = useEngineResults();
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [runIds, setRunIds] = useState<Record<string, string>>({});
  const [activeEngine, setActiveEngine] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const { query } = useSearch();

  const sortedEngines = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return engines
      .slice()
      .sort((a, b) => a.localeCompare(b))
      .filter((engineId) => {
        if (!normalizedQuery) return true;
        const label = engineId;
        return (
          engineId.toLowerCase().includes(normalizedQuery) ||
          label.toLowerCase().includes(normalizedQuery)
        );
      });
  }, [engines, query]);

  if (isLoading) {
    return <p className="text-sm text-[var(--ink-3)]">{t("states.loading")}</p>;
  }

  if (isError) {
    return <p className="text-sm text-[var(--accent-error)]">{t("states.error")}</p>;
  }

  return (
    <>
      <div className="space-y-3">
        {sortedEngines.length === 0 ? (
          <p className="text-sm text-[var(--ink-3)]">{t("states.empty")}</p>
        ) : (
          sortedEngines.map((engineId, index) => (
            <EngineCard
              key={engineId}
              engineId={engineId}
              datasetVersionId={datasetVersionId}
              index={index}
              onOpenDetail={() => {
                setActiveEngine(engineId);
                setDetailOpen(true);
              }}
              onResult={(kind, result) => {
                setResults((prev) => ({ ...prev, [engineId]: result }));
                if (datasetVersionId && result) {
                  engineResults.record({
                    engineId,
                    datasetVersionId,
                    kind,
                    payload: result,
                  });
                }
                if (result && typeof result === "object" && "run_id" in result) {
                  const runId = String((result as { run_id?: string }).run_id || "");
                  if (runId) {
                    setRunIds((prev) => ({ ...prev, [engineId]: runId }));
                  }
                }
              }}
              runId={runIds[engineId]}
              hasResult={
                Boolean(results[engineId]) ||
                Boolean(datasetVersionId && engineResults.getLatest({ engineId, datasetVersionId }))
              }
            />
          ))
        )}
      </div>
      <Modal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={activeEngine ?? t("engine.details")}
        size="lg"
      >
        <div className="space-y-6 text-sm text-[var(--ink-2)]">
          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("modal.sections.data")}
            </p>
            {(() => {
              if (!activeEngine) return <p>{t("engine.noResult")}</p>;
              const payload =
                results[activeEngine] ||
                (datasetVersionId
                  ? engineResults.getLatest({ engineId: activeEngine, datasetVersionId })?.payload
                  : undefined);
              if (!payload) {
                return <p>{t("engine.noResult")}</p>;
              }

              const evidenceIds = extractEvidenceIds(payload);
              const headline = extractHeadline(payload, t);

              return (
                <div className="space-y-3">
                  <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
                    <p className="text-sm font-semibold text-[var(--ink-1)]">{headline}</p>
                    <p className="mt-2 text-xs text-[var(--ink-3)]">{t("engine.resultReady")}</p>
                  </div>
                  <details className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4">
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                      {t("engine.viewRaw", { defaultValue: "View raw payload" })}
                    </summary>
                    <pre className="mt-3 max-h-64 overflow-y-auto rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-3 text-xs text-[var(--ink-2)]">
                      {JSON.stringify(payload, null, 2)}
                    </pre>
                  </details>
                  {evidenceIds.length ? (
                    <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                        {t("evidence.label", { defaultValue: "Evidence" })}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {evidenceIds.map((id) => (
                          <Link
                            key={id}
                            href={`/evidence/${encodeURIComponent(id)}`}
                            className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1 text-xs text-[var(--ink-2)] underline-offset-4 hover:underline"
                          >
                            {id.slice(0, 12)}
                          </Link>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-3 text-xs text-[var(--ink-3)]">
                      {t("evidence.none", { defaultValue: "No evidence linked to this result." })}
                    </div>
                  )}
                </div>
              );
            })()}
          </section>
          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("modal.sections.insights")}
            </p>
            {(() => {
              const payload =
                activeEngine && datasetVersionId
                  ? engineResults.getLatest({ engineId: activeEngine, datasetVersionId })?.payload
                  : undefined;
              const insights = extractInsights(payload, t);
              if (!insights.length) {
                return (
                  <p className="text-sm text-[var(--ink-3)]">
                    {t("engine.noInsights", {
                      defaultValue: "No insights available until a calculation is run.",
                    })}
                  </p>
                );
              }
              return (
                <ul className="space-y-2">
                  {insights.map((item) => (
                    <li
                      key={item}
                      className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-3 text-sm text-[var(--ink-2)]"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              );
            })()}
          </section>
        </div>
      </Modal>
    </>
  );
}

function extractEvidenceIds(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const obj = payload as Record<string, unknown>;

  const direct = obj.evidence_ids;
  if (Array.isArray(direct)) {
    return direct.filter((id): id is string => typeof id === "string" && id.length > 0);
  }

  const evidence = obj.evidence;
  if (Array.isArray(evidence)) {
    return evidence
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const e = item as Record<string, unknown>;
        const id = e.evidence_id ?? e.id;
        return typeof id === "string" ? id : null;
      })
      .filter((id): id is string => typeof id === "string" && id.length > 0);
  }

  return [];
}

function EngineCard({
  engineId,
  datasetVersionId,
  onResult,
  onOpenDetail,
  runId,
  hasResult,
  index,
}: {
  engineId: string;
  datasetVersionId: string | null;
  onResult: (kind: EngineResultKind, result: unknown) => void;
  onOpenDetail: () => void;
  runId?: string;
  hasResult: boolean;
  index: number;
}) {
  const { t } = useTranslation();
  const engine = useEngine(engineId);
  const label = engine.display_name;
  const hasDataset = Boolean(datasetVersionId);
  const endpointsQuery = useEngineEndpoints(engineId);
  const runSupported = endpointsQuery.data?.run.exists ?? false;
  const reportSupported = endpointsQuery.data?.report.exists ?? false;
  const canRun = hasDataset && runSupported;
  const canReport = hasDataset && reportSupported && Boolean(runId);
  const runMutation = useEngineRun(engineId);
  const reportMutation = useEngineReport(engineId);

  return (
    <div
      className={`rounded-2xl border p-4 ${
        index % 2 === 0
          ? "border-green-500/30 bg-green-500/10"
          : "border-blue-500/30 bg-blue-500/10"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {t("engine.label")}
          </p>
          <h4 className="mt-1 text-base font-semibold text-[var(--ink-1)]">
            {label}
          </h4>
        </div>
        <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1 text-xs font-semibold text-[var(--ink-3)]">
          {engineId}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          disabled={!canRun}
          loading={runMutation.isPending}
          onClick={async () => {
            if (!datasetVersionId) return;
            if (!runSupported) return;
            const payload: Record<string, unknown> = {
              dataset_version_id: datasetVersionId,
              started_at: new Date().toISOString(),
              parameters: {},
            };

            if (engineId === "engine_audit_readiness") {
              payload.regulatory_frameworks = [];
            }

            try {
              const data = await runMutation.mutateAsync(payload as never);
              onResult("run", data);
            } catch {
              onResult("run", null);
            }
          }}
        >
          {runSupported ? t("engine.run") : t("engine.unsupported", { defaultValue: "Unsupported" })}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={!hasDataset || !canReport}
          loading={reportMutation.isPending}
          onClick={async () => {
            if (!datasetVersionId) return;
            if (!reportSupported || !runId) return;
            try {
              const data = await reportMutation.mutateAsync({
                dataset_version_id: datasetVersionId,
                ...(runId ? { run_id: runId } : {}),
              });
              onResult("report", data);
            } catch {
              onResult("report", null);
            }
          }}
        >
          {t("engine.report")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenDetail}
        >
          {t("engine.details")}
        </Button>
      </div>
      {!hasDataset ? (
        <div className="mt-3 text-xs text-[var(--ink-3)]">
          {t("datasets.required", { defaultValue: "Select a dataset to run engines." })}
        </div>
      ) : null}
      {hasDataset && reportSupported && !runId ? (
        <div className="mt-1 text-xs text-[var(--ink-3)]">
          {t("engine.runBeforeReport", { defaultValue: "Run the engine to generate a report." })}
        </div>
      ) : null}
      <div className="mt-3 text-xs text-[var(--ink-3)]">
        {hasResult ? t("engine.resultReady") : t("engine.noResult")}
      </div>
    </div>
  );
}

function extractHeadline(payload: unknown, t: (key: string, options?: { defaultValue?: string; [key: string]: unknown }) => string): string {
  if (!payload || typeof payload !== "object") return t("engine.resultReady", { defaultValue: "Result available" });
  const obj = payload as Record<string, unknown>;
  if (typeof obj.findings_count === "number") {
    return t("engine.headline.findings", { count: obj.findings_count, defaultValue: `Findings: ${obj.findings_count}` });
  }
  if (typeof obj.run_id === "string") {
    return t("engine.headline.run", { runId: obj.run_id, defaultValue: `Run: ${obj.run_id}` });
  }
  if (typeof obj.engine_id === "string") {
    return t("engine.headline.engine", { engineId: obj.engine_id, defaultValue: `Engine: ${obj.engine_id}` });
  }
  return t("engine.resultReady", { defaultValue: "Result available" });
}

function extractInsights(payload: unknown, t: (key: string, options?: { defaultValue?: string; [key: string]: unknown }) => string): string[] {
  if (!payload || typeof payload !== "object") return [];
  const obj = payload as Record<string, unknown>;
  const items: string[] = [];

  if (typeof obj.findings_count === "number") {
    items.push(t("engine.insights.findingsDetected", { count: obj.findings_count, defaultValue: `Findings detected: ${obj.findings_count}` }));
  }

  const evidenceIds = extractEvidenceIds(payload);
  if (evidenceIds.length) {
    items.push(t("engine.insights.evidenceLinked", { count: evidenceIds.length, defaultValue: `Evidence linked: ${evidenceIds.length}` }));
  }

  const regulatory = obj.regulatory_results;
  if (Array.isArray(regulatory)) {
    items.push(t("engine.insights.frameworksAssessed", { count: regulatory.length, defaultValue: `Frameworks assessed: ${regulatory.length}` }));
    const notReady = regulatory.filter((r) => {
      if (!r || typeof r !== "object") return false;
      const status = (r as Record<string, unknown>).check_status;
      return status !== "ready";
    }).length;
    if (notReady) {
      items.push(t("engine.insights.notReady", { count: notReady, defaultValue: `Not ready: ${notReady}` }));
    }
  }

  return items;
}
