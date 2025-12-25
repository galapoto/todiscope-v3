"use client";

import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useEngines } from "@/hooks/use-engines";
import { useQuery } from "@tanstack/react-query";
import { api, type ProbeResult } from "@/lib/api-client";
import Link from "next/link";

type CapabilityKey = "data" | "analytics" | "reports" | "evidence" | "ai" | "workflow" | "ocr";
type SurfaceKey =
  | "dashboardWidget"
  | "reportView"
  | "drilldownModal"
  | "evidenceViewer"
  | "aiPanel"
  | "exportPaths";

type ParityStatus = "ok" | "limited" | "missing" | "na";

type EngineProbe = {
  run: ProbeResult;
  report: ProbeResult;
};

type PlatformProbe = {
  auditLogs: ProbeResult;
  evidence: ProbeResult;
  workflow: ProbeResult;
  ai: ProbeResult;
  ocr: ProbeResult;
};

function humanizeEngineId(engineId: string) {
  const spaced = engineId.replace(/[-_]+/g, " ").trim();
  return spaced.replace(/\b\w/g, (match) => match.toUpperCase());
}

function statusChip(status: ParityStatus) {
  switch (status) {
    case "ok":
      return "✅";
    case "limited":
      return "⚠️";
    case "missing":
      return "❌";
    case "na":
    default:
      return "—";
  }
}

function parity(
  backendExists: boolean,
  frontendExists: boolean,
  limitedReason?: string
): { status: ParityStatus; note?: string } {
  if (!backendExists) return { status: "na" };
  if (frontendExists) {
    return limitedReason ? { status: "limited", note: limitedReason } : { status: "ok" };
  }
  return { status: "missing", note: "Missing frontend surface" };
}

export function EngineCoverageMatrix() {
  const { t } = useTranslation();
  const enginesQuery = useEngines();
  const engines = enginesQuery.data ?? [];

  const probesQuery = useQuery({
    queryKey: ["parity-probes", engines],
    enabled: enginesQuery.isSuccess && engines.length > 0, // Only probe if engines are available
    staleTime: 60_000,
    retry: false,
    refetchOnMount: false, // Don't refetch on mount if data exists
    refetchOnWindowFocus: false, // Don't refetch on window focus
    queryFn: async (): Promise<{ engines: Record<string, EngineProbe>; platform: PlatformProbe }> => {
      const platformEntries = await Promise.all([
        api.probeEndpoint("/api/v3/audit/logs?action_type=import&limit=1"),
        api.probeEndpoint("/api/v3/evidence?finding_id=_probe"),
        api.probeEndpoint("/api/v3/workflow/finding/_probe/history"),
        api.probeEndpoint("/api/v3/ai/query"),
        api.probeEndpoint("/api/v3/ocr/upload"),
      ]);

      const platform: PlatformProbe = {
        auditLogs: platformEntries[0],
        evidence: platformEntries[1],
        workflow: platformEntries[2],
        ai: platformEntries[3],
        ocr: platformEntries[4],
      };

      const engineProbes = await Promise.all(
        engines.map(async (engineId) => {
          const [run, report] = await Promise.all([
            api.probeEngineEndpoint(engineId, "run"),
            api.probeEngineEndpoint(engineId, "report"),
          ]);
          return [engineId, { run, report }] as const;
        })
      );

      return { engines: Object.fromEntries(engineProbes), platform };
    },
  });

  const frontendSurfaces: Record<SurfaceKey, boolean> = {
    dashboardWidget: true,
    reportView: true,
    drilldownModal: true,
    evidenceViewer: true,
    aiPanel: true,
    exportPaths: true,
  };

  const rows = useMemo(() => {
    const probeData = probesQuery.data;
    const platform = probeData?.platform;

    const platformExists = {
      auditLogs: platform?.auditLogs.exists ?? false,
      evidence: platform?.evidence.exists ?? false,
      workflow: platform?.workflow.exists ?? false,
      ai: platform?.ai.exists ?? false,
      ocr: platform?.ocr.exists ?? false,
    };

    return engines.map((engineId) => {
      const engineName = t(`engines.${engineId}.name`, {
        defaultValue: humanizeEngineId(engineId),
      });

      const engineProbe = probeData?.engines?.[engineId];
      const runExists = engineProbe?.run.exists ?? false;
      const reportExists = engineProbe?.report.exists ?? false;

      const capability: Record<CapabilityKey, { status: ParityStatus; note?: string }> = {
        data: parity(runExists, frontendSurfaces.dashboardWidget),
        analytics: parity(runExists, frontendSurfaces.dashboardWidget),
        reports: parity(reportExists, frontendSurfaces.reportView),
        evidence: parity(
          platformExists.evidence,
          frontendSurfaces.evidenceViewer,
          platform?.evidence.ok ? undefined : platform?.evidence.error || undefined
        ),
        ai: parity(platformExists.ai, frontendSurfaces.aiPanel),
        workflow: parity(platformExists.workflow, true),
        ocr: parity(platformExists.ocr, true),
      };

      const surface: Record<SurfaceKey, { status: ParityStatus; note?: string }> = {
        dashboardWidget: { status: "ok" },
        reportView: { status: "ok" },
        drilldownModal: { status: "ok" },
        evidenceViewer: parity(platformExists.evidence, true),
        aiPanel: parity(platformExists.ai, true),
        exportPaths: parity(
          reportExists || platformExists.auditLogs,
          true,
          platformExists.auditLogs && !platform?.auditLogs.ok
            ? t("coverage.notes.exportsLimited", {
                defaultValue: "Exports are available, but dataset-backed exports may fail without DB configuration.",
              })
            : undefined
        ),
      };

      const notes: string[] = [];
      if (platform?.auditLogs.exists && !platform?.auditLogs.ok) {
        notes.push(
          t("coverage.notes.auditLogsLimited", {
            defaultValue:
              "Dataset discovery uses audit logs; backend may return 500 when DB is not configured.",
          })
        );
      }
      if (!runExists) {
        notes.push(
          t("coverage.notes.noRunEndpoint", {
            defaultValue: "No engine run endpoint detected for this engine.",
          })
        );
      }
      if (!reportExists) {
        notes.push(
          t("coverage.notes.noReportEndpoint", {
            defaultValue: "No engine report endpoint detected for this engine.",
          })
        );
      }

      return { engineId, engineName, capability, surface, notes };
    });
  }, [engines, probesQuery.data, t]);

  const hasMissing = rows.some((row) =>
    [...Object.values(row.capability), ...Object.values(row.surface)].some(
      (cell) => cell.status === "missing"
    )
  );

  const anyLimited = rows.some((row) =>
    [...Object.values(row.capability), ...Object.values(row.surface)].some(
      (cell) => cell.status === "limited"
    )
  );

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[var(--ink-1)]">
              {t("coverage.parityTitle", { defaultValue: "Frontend–Backend Parity Matrix" })}
            </h3>
            <p className="mt-1 text-xs text-[var(--ink-3)]">
              {t("coverage.paritySubtitle", {
                defaultValue:
                  "Generated from enabled engines + runtime probing. ✅ parity, ⚠️ limited, ❌ missing.",
              })}
            </p>
          </div>
          <div
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              hasMissing
                ? "bg-[var(--accent-error)]/15 text-[var(--accent-error)]"
                : anyLimited
                  ? "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]"
                  : "bg-[var(--accent-success)]/15 text-[var(--accent-success)]"
            }`}
          >
            {hasMissing
              ? t("coverage.status.blocked", { defaultValue: "Blocked" })
              : anyLimited
                ? t("coverage.status.limited", { defaultValue: "Limited" })
                : t("coverage.status.ready", { defaultValue: "Ready" })}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--ink-3)]">
          <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
            {t("coverage.links.dashboard", { defaultValue: "Dashboard" })}:{" "}
            <Link href="/dashboard" className="underline underline-offset-4">
              /dashboard
            </Link>
          </span>
          <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
            {t("coverage.links.reports", { defaultValue: "Reports" })}:{" "}
            <Link href="/reports" className="underline underline-offset-4">
              /reports
            </Link>
          </span>
          <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
            {t("coverage.links.settings", { defaultValue: "Settings" })}:{" "}
            <Link href="/settings" className="underline underline-offset-4">
              /settings
            </Link>
          </span>
        </div>
      </div>

      {enginesQuery.isLoading || probesQuery.isLoading ? (
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-3)]">
          {t("coverage.loading", { defaultValue: "Loading parity matrix..." })}
        </div>
      ) : enginesQuery.isError ? (
        <div className="rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
          {t("coverage.errorEngines", { defaultValue: "Failed to load enabled engines." })}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)]">
          <table className="min-w-[980px] w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-3)] bg-[var(--surface-2)]">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
                  {t("coverage.engine", { defaultValue: "Engine" })}
                </th>
                <th
                  className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]"
                  colSpan={7}
                >
                  {t("coverage.backendCapabilities", { defaultValue: "Backend Capabilities" })}
                </th>
                <th
                  className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]"
                  colSpan={6}
                >
                  {t("coverage.frontendSurfaces", { defaultValue: "Frontend Surfaces" })}
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
                  {t("coverage.notes", { defaultValue: "Notes" })}
                </th>
              </tr>
              <tr className="border-b border-[var(--surface-3)] bg-[var(--surface-2)]">
                <th />
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.data", { defaultValue: "Data" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.analytics", { defaultValue: "Analytics" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.reports", { defaultValue: "Reports" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.evidence", { defaultValue: "Evidence" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.ai", { defaultValue: "AI" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.workflow", { defaultValue: "Workflow" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.capabilities.ocr", { defaultValue: "OCR" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.widget", { defaultValue: "Widget" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.report", { defaultValue: "Report view" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.drilldown", { defaultValue: "Drill-down" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.evidence", { defaultValue: "Evidence viewer" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.ai", { defaultValue: "AI panel" })}
                </th>
                <th className="px-2 py-2 text-center text-xs font-semibold text-[var(--ink-3)]">
                  {t("coverage.surfaces.exports", { defaultValue: "Exports" })}
                </th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.engineId}
                  className="border-b border-[var(--surface-3)] transition hover:bg-[var(--surface-2)]"
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-[var(--ink-1)]">{row.engineName}</p>
                      <p className="text-xs text-[var(--ink-3)]">{row.engineId}</p>
                    </div>
                  </td>
                  {(
                    ["data", "analytics", "reports", "evidence", "ai", "workflow", "ocr"] as CapabilityKey[]
                  ).map((key) => (
                    <td key={key} className="px-2 py-3 text-center">
                      <span
                        className="text-lg"
                        title={row.capability[key].note ?? undefined}
                        aria-label={`${key}: ${row.capability[key].status}`}
                      >
                        {statusChip(row.capability[key].status)}
                      </span>
                    </td>
                  ))}
                  {(
                    [
                      "dashboardWidget",
                      "reportView",
                      "drilldownModal",
                      "evidenceViewer",
                      "aiPanel",
                      "exportPaths",
                    ] as SurfaceKey[]
                  ).map((key) => (
                    <td key={key} className="px-2 py-3 text-center">
                      <span
                        className="text-lg"
                        title={row.surface[key].note ?? undefined}
                        aria-label={`${key}: ${row.surface[key].status}`}
                      >
                        {statusChip(row.surface[key].status)}
                      </span>
                    </td>
                  ))}
                  <td className="px-4 py-3 text-xs text-[var(--ink-3)]">
                    {row.notes.length ? (
                      <ul className="list-disc pl-4">
                        {row.notes.slice(0, 3).map((note, idx) => (
                          <li key={idx}>{note}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-[var(--ink-3)]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
          {t("coverage.datasetCoverage", { defaultValue: "Dataset Coverage" })}
        </p>
        <div className="grid gap-2 text-xs text-[var(--ink-3)] sm:grid-cols-2">
          <div className="flex items-start gap-2">
            <span className="text-lg">
              {statusChip(
                probesQuery.data?.platform.auditLogs.exists
                  ? probesQuery.data.platform.auditLogs.ok
                    ? "ok"
                    : "limited"
                  : "limited"
              )}
            </span>
            <div>
              <p className="font-semibold text-[var(--ink-2)]">
                {t("coverage.datasets.discoverable", { defaultValue: "Discoverable" })}
              </p>
              <p>
                {t("coverage.datasets.discoverableBody", {
                  defaultValue:
                    "Dataset versions are derived from audit logs (`action_type=import`).",
                })}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-lg">{statusChip("ok")}</span>
            <div>
              <p className="font-semibold text-[var(--ink-2)]">
                {t("coverage.datasets.viewable", { defaultValue: "Viewable & Filterable" })}
              </p>
              <p>
                {t("coverage.datasets.viewableBody", {
                  defaultValue: "Dataset versions are shown in a table with search + pagination.",
                })}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-lg">{statusChip("ok")}</span>
            <div>
              <p className="font-semibold text-[var(--ink-2)]">
                {t("coverage.datasets.exportable", { defaultValue: "Exportable" })}
              </p>
              <p>
                {t("coverage.datasets.exportableBody", {
                  defaultValue: "CSV and XLSX exports reflect the current filtered table state.",
                })}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-lg">{statusChip("ok")}</span>
            <div>
              <p className="font-semibold text-[var(--ink-2)]">
                {t("coverage.datasets.versionAware", { defaultValue: "Version-aware" })}
              </p>
              <p>
                {t("coverage.datasets.versionAwareBody", {
                  defaultValue:
                    "Selected dataset is stored in localStorage and historical datasets are marked read-only.",
                })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
