"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { api } from "@/lib/api-client";
import { useDatasetContext } from "@/components/data/dataset-context";
import { Shield, CheckCircle2, XCircle, Clock, AlertCircle, FileText, Database, GitBranch, Calculator, ClipboardList } from "lucide-react";

type LifecycleStage = {
  stage: "import" | "normalize" | "calculate" | "report";
  status: "completed" | "failed" | "blocked" | "never_executed";
  timestamp?: string;
  engine_id?: string;
  details?: string;
};

type AuditEvent = {
  audit_log_id: string;
  dataset_version_id?: string | null;
  calculation_run_id?: string | null;
  action_type: string;
  action_label?: string | null;
  status: string;
  created_at: string;
  reason?: string | null;
  context?: Record<string, unknown> | null;
  error_message?: string | null;
};

export default function AuditPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("audit.title", { defaultValue: "Audit Surface" })}
        subtitle={t("audit.subtitle", { defaultValue: "Read-only evidence and enforcement verification" })}
      >
        <AuditSurface />
      </AppShell>
    </AuthGuard>
  );
}

function AuditSurface({ datasetVersionId: propDatasetVersionId }: { datasetVersionId?: string } = {}) {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const { datasetVersionId: contextDatasetVersionId } = useDatasetContext();
  const datasetIdFromUrl = searchParams.get("dataset_version_id");
  const engineIdFromUrl = searchParams.get("engine_id");
  const activeDatasetId = propDatasetVersionId || datasetIdFromUrl || contextDatasetVersionId || null;

  const { data: auditLogs, isLoading: logsLoading } = useQuery({
    queryKey: ["audit-logs", activeDatasetId],
    queryFn: () => api.getAuditLogs({ dataset_version_id: activeDatasetId || undefined, limit: 1000 }),
    enabled: !!activeDatasetId,
    staleTime: 30_000,
  });

  // Derive lifecycle stages from audit logs
  const lifecycleStages = deriveLifecycleStages(auditLogs?.logs || [], activeDatasetId);
  const integrityViolations = deriveIntegrityViolations(auditLogs?.logs || [], activeDatasetId);
  const runHistory = deriveRunHistory(auditLogs?.logs || [], activeDatasetId);

  // Filter audit events (chronological, immutable)
  const auditEvents: AuditEvent[] = (auditLogs?.logs || []) as AuditEvent[];

  return (
    <div className="grid gap-6">
      {/* Audit Context Header */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600/10 dark:bg-blue-400/10">
            <Shield className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-[var(--ink-1)]">
              {t("audit.context.title", { defaultValue: "Audit Context" })}
            </h3>
            {activeDatasetId ? (
              <div className="mt-2 space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-[var(--ink-3)]" />
                  <span className="font-mono text-xs text-[var(--ink-2)]">{activeDatasetId}</span>
                  <span className="rounded-full border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 px-2 py-0.5 text-xs text-[var(--accent-success)]">
                    {t("audit.context.immutable", { defaultValue: "Immutable" })}
                  </span>
                </div>
                {engineIdFromUrl && (
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[var(--ink-3)]" />
                    <span className="text-[var(--ink-2)]">
                      {t("audit.context.engine", { engineId: engineIdFromUrl, defaultValue: `Engine: ${engineIdFromUrl}` })}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="mt-2 text-sm text-[var(--ink-3)]">
                {t("audit.context.noDataset", { defaultValue: "No dataset selected. Select a dataset to view audit records." })}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Lifecycle Evidence Section */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("audit.lifecycle.title", { defaultValue: "Lifecycle Evidence" })}
        </h3>
        {logsLoading ? (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.lifecycle.loading", { defaultValue: "Loading lifecycle state..." })}
          </p>
        ) : activeDatasetId ? (
          lifecycleStages.length ? (
            <div className="space-y-3">
              {lifecycleStages.map((stage) => (
                <LifecycleStageRow key={stage.stage} stage={stage} t={t} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--ink-3)]">
              {t("audit.lifecycle.empty", { defaultValue: "No lifecycle data recorded for this dataset." })}
            </p>
          )
        ) : (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.lifecycle.noDataset", { defaultValue: "Select a dataset to view lifecycle evidence." })}
          </p>
        )}
      </section>

      {/* Enforcement Violations */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("audit.violations.title", { defaultValue: "Enforcement Violations" })}
        </h3>
        {logsLoading ? (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.violations.loading", { defaultValue: "Loading enforcement violations..." })}
          </p>
        ) : activeDatasetId ? (
          integrityViolations.length ? (
            <div className="space-y-2">
              {integrityViolations.map((event) => (
                <ViolationRow key={event.audit_log_id} event={event} t={t} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--ink-3)]">
              {t("audit.violations.empty", { defaultValue: "No enforcement violations recorded." })}
            </p>
          )
        ) : (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.violations.noDataset", { defaultValue: "Select a dataset to view enforcement violations." })}
          </p>
        )}
      </section>

      {/* Run History */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("audit.runs.title", { defaultValue: "Run History" })}
        </h3>
        {logsLoading ? (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.runs.loading", { defaultValue: "Loading run history..." })}
          </p>
        ) : activeDatasetId ? (
          runHistory.length ? (
            <div className="space-y-2">
              {runHistory.map((event) => (
                <RunHistoryRow key={event.audit_log_id} event={event} t={t} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--ink-3)]">
              {t("audit.runs.empty", { defaultValue: "No runs recorded for this dataset." })}
            </p>
          )
        ) : (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.runs.noDataset", { defaultValue: "Select a dataset to view run history." })}
          </p>
        )}
      </section>

      {/* Audit Events Log */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("audit.events.title", { defaultValue: "Audit Events Log" })}
        </h3>
        {logsLoading ? (
          <p className="text-sm text-[var(--ink-3)]">{t("audit.events.loading", { defaultValue: "Loading audit events..." })}</p>
        ) : auditEvents.length > 0 ? (
          <div className="space-y-2">
            {auditEvents.map((event) => (
              <AuditEventRow key={event.audit_log_id} event={event} t={t} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--ink-3)]">
            {t("audit.events.empty", { defaultValue: "No audit events recorded." })}
          </p>
        )}
      </section>

      {/* Assumptions & Evidence Section */}
      <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("audit.evidence.title", { defaultValue: "Assumptions & Evidence" })}
        </h3>
        <p className="text-sm text-[var(--ink-3)]">
          {t("audit.evidence.empty", { defaultValue: "No assumptions recorded. Evidence IDs are linked to findings in engine run results." })}
        </p>
      </section>
    </div>
  );
}

function LifecycleStageRow({ stage, t }: { stage: LifecycleStage; t: any }) {
  const stageIcons = {
    import: Database,
    normalize: GitBranch,
    calculate: Calculator,
    report: ClipboardList,
  };
  const stageLabels = {
    import: t("audit.lifecycle.import", { defaultValue: "Import" }),
    normalize: t("audit.lifecycle.normalize", { defaultValue: "Normalize" }),
    calculate: t("audit.lifecycle.calculate", { defaultValue: "Calculate" }),
    report: t("audit.lifecycle.report", { defaultValue: "Report" }),
  };
  const Icon = stageIcons[stage.stage];
  const statusIcons = {
    completed: CheckCircle2,
    failed: XCircle,
    blocked: AlertCircle,
    never_executed: Clock,
  };
  const StatusIcon = statusIcons[stage.status];
  const statusColors = {
    completed: "text-[var(--accent-success)]",
    failed: "text-[var(--accent-error)]",
    blocked: "text-[var(--accent-warn)]",
    never_executed: "text-[var(--ink-3)]",
  };

  return (
    <div className="flex items-center gap-4 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
      <Icon className="h-5 w-5 text-[var(--ink-3)]" />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--ink-1)]">{stageLabels[stage.stage]}</span>
          <StatusIcon className={`h-4 w-4 ${statusColors[stage.status]}`} />
        </div>
        {stage.timestamp && (
          <p className="mt-1 text-xs text-[var(--ink-3)]">
            {new Date(stage.timestamp).toLocaleString()}
          </p>
        )}
        {stage.engine_id && (
          <p className="mt-1 text-xs text-[var(--ink-3)]">
            {t("audit.lifecycle.engine", { engineId: stage.engine_id, defaultValue: `Engine: ${stage.engine_id}` })}
          </p>
        )}
        {stage.details && (
          <p className="mt-1 text-xs text-[var(--ink-3)]">{stage.details}</p>
        )}
        {stage.status === "never_executed" && (
          <p className="mt-1 text-xs text-[var(--ink-3)]">
            {t("audit.lifecycle.notExecuted", { defaultValue: "Stage has not been executed." })}
          </p>
        )}
      </div>
    </div>
  );
}

function AuditEventRow({ event, t }: { event: AuditEvent; t: any }) {
  const isRejection = event.status === "rejected" || event.status === "failed" || event.error_message;
  const isAllowed = event.status === "allowed" || event.status === "success";

  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        isRejection
          ? "border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10"
          : isAllowed
            ? "border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10"
            : "border-[var(--surface-3)] bg-[var(--surface-2)]"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-[var(--ink-1)]">{event.action_label || event.action_type}</span>
            {isRejection && (
              <span className="rounded-full border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/20 px-2 py-0.5 text-xs text-[var(--accent-error)]">
                {t("audit.events.rejected", { defaultValue: "Rejected" })}
              </span>
            )}
            {isAllowed && (
              <span className="rounded-full border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/20 px-2 py-0.5 text-xs text-[var(--accent-success)]">
                {t("audit.events.allowed", { defaultValue: "Allowed" })}
              </span>
            )}
          </div>
          {event.reason && (
            <p className="mt-1 text-xs text-[var(--ink-2)]">{event.reason}</p>
          )}
          {event.error_message && (
            <p className="mt-1 text-xs text-[var(--accent-error)]">{event.error_message}</p>
          )}
          <p className="mt-1 text-xs text-[var(--ink-3)]">
            {new Date(event.created_at).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}

function deriveLifecycleStages(logs: unknown[], datasetVersionId: string | null): LifecycleStage[] {
  if (!datasetVersionId || !Array.isArray(logs)) {
    return [];
  }

  const events = logs as AuditEvent[];
  const integrityEvents = events.filter((e) => e.action_type === "integrity");

  const stageMap: Record<LifecycleStage["stage"], { types: string[] }> = {
    import: { types: ["import"] },
    normalize: { types: ["normalization"] },
    calculate: { types: ["calculation"] },
    report: { types: ["reporting"] },
  };

  return (Object.keys(stageMap) as LifecycleStage["stage"][]).map((stage) => {
    const stageEvents = events.filter((e) => stageMap[stage].types.includes(e.action_type));
    const lastSuccess = stageEvents.find((e) => e.status === "success");
    const lastFailure = stageEvents.find((e) => e.status === "failure");
    const stageViolation = integrityEvents.find((e) => e.context && e.context["stage"] === stage);

    if (lastSuccess) {
      return {
        stage,
        status: "completed",
        timestamp: lastSuccess.created_at,
        engine_id: extractEngineId(lastSuccess),
        details: lastSuccess.reason ?? undefined,
      };
    }
    if (lastFailure) {
      return {
        stage,
        status: "failed",
        timestamp: lastFailure.created_at,
        engine_id: extractEngineId(lastFailure),
        details: lastFailure.error_message ?? lastFailure.reason ?? undefined,
      };
    }
    if (stageViolation) {
      return {
        stage,
        status: "blocked",
        timestamp: stageViolation.created_at,
        engine_id: extractEngineId(stageViolation),
        details: stageViolation.error_message ?? stageViolation.reason ?? undefined,
      };
    }
    return { stage, status: "never_executed" };
  });
}

function extractEngineId(event: AuditEvent): string | undefined {
  const context = event.context;
  if (context && typeof context === "object" && "engine_id" in context) {
    return String(context.engine_id);
  }
  return undefined;
}

function deriveIntegrityViolations(logs: unknown[], datasetVersionId: string | null): AuditEvent[] {
  if (!datasetVersionId || !Array.isArray(logs)) return [];
  const events = logs as AuditEvent[];
  return events
    .filter((e) => e.action_type === "integrity")
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
}

function deriveRunHistory(logs: unknown[], datasetVersionId: string | null): AuditEvent[] {
  if (!datasetVersionId || !Array.isArray(logs)) return [];
  const events = logs as AuditEvent[];
  return events
    .filter((e) => e.action_type === "calculation")
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
}

function ViolationRow({ event, t }: { event: AuditEvent; t: any }) {
  const context = event.context ?? {};
  const attemptedAction =
    typeof context === "object" && "attempted_action" in context ? String(context.attempted_action) : "unknown";
  const engineId =
    typeof context === "object" && "engine_id" in context ? String(context.engine_id) : "unknown";

  return (
    <div className="rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--accent-error)]">
        <span className="rounded-full border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/20 px-2 py-0.5">
          {t("audit.violations.label", { defaultValue: "Violation" })}
        </span>
        <span>{t("audit.violations.action", { defaultValue: "Action" })}: {attemptedAction}</span>
        <span>{t("audit.violations.engine", { defaultValue: "Engine" })}: {engineId}</span>
      </div>
      <p className="mt-2 text-sm text-[var(--ink-2)]">{event.error_message ?? event.reason}</p>
      <p className="mt-1 text-xs text-[var(--ink-3)]">
        {new Date(event.created_at).toLocaleString()}
      </p>
    </div>
  );
}

function RunHistoryRow({ event, t }: { event: AuditEvent; t: any }) {
  const runId = event.calculation_run_id || extractRunId(event);
  const engineId = extractEngineId(event);
  const statusLabel =
    event.status === "success" ? t("audit.runs.success", { defaultValue: "Success" }) : t("audit.runs.failed", { defaultValue: "Failed" });

  return (
    <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {t("audit.runs.runId", { defaultValue: "Run ID" })}
          </p>
          <p className="text-xs text-[var(--ink-2)]">{runId || "--"}</p>
        </div>
        <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-2 py-0.5 text-xs text-[var(--ink-3)]">
          {statusLabel}
        </span>
      </div>
      <div className="mt-2 text-xs text-[var(--ink-3)]">
        <p>{t("audit.runs.engine", { defaultValue: "Engine" })}: {engineId || "--"}</p>
        <p>{t("audit.runs.dataset", { defaultValue: "Dataset" })}: {event.dataset_version_id || "--"}</p>
        <p>{t("audit.runs.time", { defaultValue: "Execution time" })}: {new Date(event.created_at).toLocaleString()}</p>
      </div>
    </div>
  );
}

function extractRunId(event: AuditEvent): string | null {
  const context = event.context;
  if (context && typeof context === "object" && "calculation_run_id" in context) {
    return String(context.calculation_run_id);
  }
  return null;
}
