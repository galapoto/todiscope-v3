"use client";

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDatasetContext } from "@/components/data/dataset-context";
import { useEngineResults } from "@/components/engines/engine-results-context";
import { Card } from "@/components/ui/card";
import { Modal } from "@/components/ui/modal";
import Link from "next/link";

type MetricId = "enginesRun" | "findings" | "evidence" | "latestRun";

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

function extractFindingsCount(payload: unknown): number | null {
  if (!payload || typeof payload !== "object") return null;
  const obj = payload as Record<string, unknown>;
  const value = obj.findings_count;
  return typeof value === "number" ? value : null;
}

export function DashboardOverview() {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();
  const engineResults = useEngineResults();
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeMetric, setActiveMetric] = useState<MetricId | null>(null);

  const datasetResults = useMemo(() => {
    if (!datasetVersionId) return [];
    return engineResults.getAllForDataset(datasetVersionId);
  }, [datasetVersionId, engineResults]);

  const metrics = useMemo(() => {
    if (!datasetVersionId) return null;
    if (!datasetResults.length) return { empty: true } as const;

    const engineIds = new Set(datasetResults.map((r) => r.engineId));
    const findingsTotal = datasetResults.reduce((sum, r) => {
      const value = extractFindingsCount(r.payload);
      return sum + (value ?? 0);
    }, 0);
    const evidenceIds = new Set<string>();
    datasetResults.forEach((r) => {
      extractEvidenceIds(r.payload).forEach((id) => evidenceIds.add(id));
    });
    const latest = datasetResults[0]?.recordedAt;

    return {
      empty: false,
      enginesRun: engineIds.size,
      findings: findingsTotal,
      evidence: evidenceIds.size,
      latestRun: latest ?? null,
      evidenceList: Array.from(evidenceIds).slice(0, 8),
    } as const;
  }, [datasetResults, datasetVersionId]);

  const cards: Array<{ id: MetricId; label: string; value: string; help: string }> = [
    {
      id: "enginesRun",
      label: t("dashboard.metrics.enginesRun", { defaultValue: "Engines run" }),
      value: metrics?.empty ? "--" : String(metrics?.enginesRun ?? "--"),
      help: t("dashboard.metrics.enginesRunHelp", {
        defaultValue: "Number of engines executed for the selected dataset version.",
      }),
    },
    {
      id: "findings",
      label: t("dashboard.metrics.findings", { defaultValue: "Findings" }),
      value: metrics?.empty ? "--" : String(metrics?.findings ?? "--"),
      help: t("dashboard.metrics.findingsHelp", {
        defaultValue: "Sum of findings reported by engines that expose a findings count.",
      }),
    },
    {
      id: "evidence",
      label: t("dashboard.metrics.evidence", { defaultValue: "Evidence linked" }),
      value: metrics?.empty ? "--" : String(metrics?.evidence ?? "--"),
      help: t("dashboard.metrics.evidenceHelp", {
        defaultValue: "Unique evidence IDs referenced by the latest engine outputs.",
      }),
    },
    {
      id: "latestRun",
      label: t("dashboard.metrics.latestRun", { defaultValue: "Latest run" }),
      value:
        metrics && metrics.empty
          ? "--"
          : metrics?.latestRun
            ? new Date(metrics.latestRun).toLocaleString()
            : "--",
      help: t("dashboard.metrics.latestRunHelp", {
        defaultValue: "Timestamp of the most recent engine output stored for this dataset version.",
      }),
    },
  ];

  if (!datasetVersionId) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">
          {t("datasets.required", { defaultValue: "Select a dataset to view dashboard metrics." })}
        </p>
      </div>
    );
  }

  if (metrics?.empty) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">
          {t("dashboard.noRuns", { defaultValue: "No report has been run yet." })}
        </p>
        <p className="mt-2 text-[var(--ink-3)]">
          {t("dashboard.noRunsBody", { defaultValue: "Run a calculation to see real metrics and charts." })}
        </p>
        <Link href="/reports" className="mt-4 inline-flex text-[var(--accent-1)] underline underline-offset-4">
          {t("dashboard.goToReports", { defaultValue: "Go to reports" })}
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        {cards.map((metric, index) => (
          <Card
            key={metric.id}
            variant="muted"
            resizable
            hoverable
            className={`cursor-pointer p-4 ${
              index % 2 === 0
                ? "border-green-500/30 bg-green-500/10"
                : "border-blue-500/30 bg-blue-500/10"
            }`}
            onClick={() => {
              setActiveMetric(metric.id);
              setDetailOpen(true);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                setActiveMetric(metric.id);
                setDetailOpen(true);
              }
            }}
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {metric.label}
            </p>
            <div className="mt-3">
              <span className="text-2xl font-semibold text-[var(--ink-1)]">{metric.value}</span>
            </div>
          </Card>
        ))}
      </div>

      <Modal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={t("dashboard.metricDetail", { defaultValue: "Metric detail" })}
        size="lg"
      >
        <div className="space-y-4 text-sm text-[var(--ink-2)]">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {activeMetric ? cards.find((c) => c.id === activeMetric)?.label : "--"}
          </p>
          <p className="text-[var(--ink-3)]">
            {activeMetric ? cards.find((c) => c.id === activeMetric)?.help : "--"}
          </p>
          {activeMetric === "evidence" && metrics?.evidenceList?.length ? (
            <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("evidence.label", { defaultValue: "Evidence" })}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {metrics.evidenceList.map((id) => (
                  <Link
                    key={id}
                    href={`/evidence/${encodeURIComponent(id)}`}
                    className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1 text-xs text-[var(--ink-2)] underline-offset-4 hover:underline"
                  >
                    {id.slice(0, 12)}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </Modal>
    </>
  );
}
