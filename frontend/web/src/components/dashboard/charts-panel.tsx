"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTranslation } from "react-i18next";
import { useMemo, useState } from "react";
import { Modal } from "@/components/ui/modal";
import { useDatasetContext } from "@/components/data/dataset-context";
import { useEngineResults } from "@/components/engines/engine-results-context";
import Link from "next/link";

const pieColors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)"];

type ChartPoint = { name: string; value: number; meta?: Record<string, unknown> };

function safeNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function safeString(value: unknown) {
  return typeof value === "string" ? value : null;
}

function countEvidenceIds(payload: unknown): number | null {
  if (!payload || typeof payload !== "object") return null;
  const anyPayload = payload as Record<string, unknown>;
  const direct = anyPayload.evidence_ids;
  if (Array.isArray(direct)) return direct.length;

  const traceability = anyPayload.traceability;
  if (traceability && typeof traceability === "object") {
    const tr = traceability as Record<string, unknown>;
    const ids = tr.inputs_evidence_ids;
    const assumptions = tr.assumptions_evidence_id;
    let count = 0;
    if (Array.isArray(ids)) count += ids.length;
    if (typeof assumptions === "string") count += 1;
    return count || null;
  }

  return null;
}

function extractEvidenceIds(payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const anyPayload = payload as Record<string, unknown>;
  const ids = anyPayload.evidence_ids;
  if (Array.isArray(ids)) return ids.map((id) => String(id)).filter(Boolean);
  return [];
}

export function ChartsPanel() {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();
  const { getAllForDataset } = useEngineResults();
  const [activePoint, setActivePoint] = useState<ChartPoint | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const datasetResults = useMemo(() => {
    if (!datasetVersionId) return [];
    return getAllForDataset(datasetVersionId);
  }, [datasetVersionId, getAllForDataset]);

  const latestByEngine = useMemo(() => {
    const map = new Map<string, { engineId: string; payload: unknown }>();
    for (const item of datasetResults) {
      if (!map.has(item.engineId)) {
        map.set(item.engineId, { engineId: item.engineId, payload: item.payload });
      }
    }
    return Array.from(map.values());
  }, [datasetResults]);

  const findingsByEngine = useMemo<ChartPoint[]>(() => {
    return latestByEngine
      .map((item) => {
        if (!item.payload || typeof item.payload !== "object") return null;
        const anyPayload = item.payload as Record<string, unknown>;
        const findings = safeNumber(anyPayload.findings_count);
        if (findings === null) return null;
        return {
          name: item.engineId,
          value: findings,
          meta: { engineId: item.engineId },
        } satisfies ChartPoint;
      })
      .filter(Boolean) as ChartPoint[];
  }, [latestByEngine]);

  const evidenceByEngine = useMemo<ChartPoint[]>(() => {
    return latestByEngine
      .map((item) => {
        const evidenceCount = countEvidenceIds(item.payload);
        if (evidenceCount === null) return null;
        return {
          name: item.engineId,
          value: evidenceCount,
          meta: {
            engineId: item.engineId,
            evidenceIds: extractEvidenceIds(item.payload),
          },
        } satisfies ChartPoint;
      })
      .filter(Boolean) as ChartPoint[];
  }, [latestByEngine]);

  const auditReadinessControlsFailing = useMemo<ChartPoint[]>(() => {
    const candidates = latestByEngine.filter((item) => item.engineId === "engine_audit_readiness");
    const payload = candidates[0]?.payload;
    if (!payload || typeof payload !== "object") return [];
    const anyPayload = payload as Record<string, unknown>;
    const results = anyPayload.regulatory_results;
    if (!Array.isArray(results)) return [];
    return results
      .map((entry) => {
        if (!entry || typeof entry !== "object") return null;
        const e = entry as Record<string, unknown>;
        const name =
          safeString(e.framework_name) ??
          safeString(e.framework_id) ??
          t("engines.engine_audit_readiness.name", { defaultValue: "Audit readiness" });
        const failing = safeNumber(e.controls_failing);
        if (failing === null) return null;
        return {
          name,
          value: failing,
          meta: {
            frameworkId: safeString(e.framework_id) ?? undefined,
            evidenceIds: Array.isArray(e.evidence_ids)
              ? e.evidence_ids.map((id) => String(id)).filter(Boolean)
              : [],
          },
        } satisfies ChartPoint;
      })
      .filter(Boolean) as ChartPoint[];
  }, [latestByEngine, t]);

  const hasAnyCharts =
    findingsByEngine.length > 0 || evidenceByEngine.length > 0 || auditReadinessControlsFailing.length > 0;

  return (
    <>
      {!datasetVersionId ? (
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
          {t("dashboard.charts.noDataset", {
            defaultValue: "Select a dataset to see charts derived from engine results.",
          })}
        </div>
      ) : !hasAnyCharts ? (
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
          {t("dashboard.charts.empty", {
            defaultValue: "No chartable results yet. Run an engine or generate a report to populate charts.",
          })}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {findingsByEngine.length ? (
            <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("dashboard.charts.findingsByEngine", {
                  defaultValue: "Findings by engine",
                })}
              </p>
              <div className="mt-4 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={findingsByEngine}>
                    <XAxis dataKey="name" stroke="var(--ink-3)" fontSize={10} />
                    <YAxis stroke="var(--ink-3)" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface-1)",
                        borderRadius: 12,
                        borderColor: "var(--surface-3)",
                        color: "var(--ink-1)",
                      }}
                    />
                    <Bar
                      dataKey="value"
                      fill="var(--chart-2)"
                      radius={[8, 8, 0, 0]}
                      onClick={(data) => {
                        if (data && "name" in data && "value" in data) {
                          setActivePoint({
                            name: String(data.name),
                            value: Number(data.value),
                            meta: { engineId: String(data.name) },
                          });
                          setDetailOpen(true);
                        }
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {evidenceByEngine.length ? (
            <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("dashboard.charts.evidenceByEngine", {
                  defaultValue: "Evidence by engine",
                })}
              </p>
              <div className="mt-4 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface-1)",
                        borderRadius: 12,
                        borderColor: "var(--surface-3)",
                        color: "var(--ink-1)",
                      }}
                    />
                    <Pie
                      data={evidenceByEngine}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={4}
                      onClick={(data) => {
                        if (data && "name" in data && "value" in data) {
                          const point = evidenceByEngine.find((p) => p.name === String(data.name));
                          setActivePoint(point ?? { name: String(data.name), value: Number(data.value) });
                          setDetailOpen(true);
                        }
                      }}
                    >
                      {evidenceByEngine.map((entry, index) => (
                        <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}

          {auditReadinessControlsFailing.length ? (
            <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 lg:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {t("dashboard.charts.controlsFailing", {
                  defaultValue: "Audit readiness: failing controls",
                })}
              </p>
              <div className="mt-4 h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={auditReadinessControlsFailing}>
                    <XAxis dataKey="name" stroke="var(--ink-3)" fontSize={10} />
                    <YAxis stroke="var(--ink-3)" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface-1)",
                        borderRadius: 12,
                        borderColor: "var(--surface-3)",
                        color: "var(--ink-1)",
                      }}
                    />
                    <Bar
                      dataKey="value"
                      fill="var(--chart-1)"
                      radius={[8, 8, 0, 0]}
                      onClick={(data) => {
                        if (data && "name" in data && "value" in data) {
                          const point = auditReadinessControlsFailing.find((p) => p.name === String(data.name));
                          setActivePoint(point ?? { name: String(data.name), value: Number(data.value) });
                          setDetailOpen(true);
                        }
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : null}
        </div>
      )}
      <Modal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={t("charts.detailTitle", { defaultValue: "Detail" })}
        size="md"
      >
        <div className="space-y-6 text-sm text-[var(--ink-2)]">
          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("modal.sections.data", { defaultValue: "Data" })}
            </p>
            <p>
              {t("charts.detailLabel", { defaultValue: "Label" })}: {activePoint?.name ?? "--"}
            </p>
            <p>
              {t("charts.detailValue", { defaultValue: "Value" })}: {activePoint?.value ?? "--"}
            </p>
          </section>
          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("modal.sections.insights", { defaultValue: "Context" })}
            </p>
            <div className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-3 text-xs text-[var(--ink-3)]">
              <p>
                {t("datasets.id", { defaultValue: "Dataset" })}:{" "}
                <span className="font-mono text-[var(--ink-2)]">{datasetVersionId ?? "--"}</span>
              </p>
              {activePoint?.meta?.engineId ? (
                <p className="mt-1">
                  {t("coverage.engine", { defaultValue: "Engine" })}:{" "}
                  <span className="font-mono text-[var(--ink-2)]">
                    {String(activePoint.meta.engineId)}
                  </span>
                </p>
              ) : null}
            </div>
          </section>
          <section className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("modal.sections.evidence", { defaultValue: "Evidence" })}
            </p>
            {Array.isArray(activePoint?.meta?.evidenceIds) && (activePoint?.meta?.evidenceIds as unknown[]).length ? (
              <div className="flex flex-wrap gap-2">
                {(activePoint?.meta?.evidenceIds as unknown[]).slice(0, 12).map((id) => (
                  <Link
                    key={String(id)}
                    href={`/evidence/${String(id)}`}
                    className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1 text-xs text-[var(--ink-2)] underline underline-offset-4"
                  >
                    {String(id).slice(0, 10)}
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--ink-3)]">
                {t("evidence.none", { defaultValue: "No evidence links available for this point." })}
              </p>
            )}
          </section>
        </div>
      </Modal>
    </>
  );
}
