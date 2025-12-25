"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "@/lib/api-client";
import { useDatasetContext } from "@/components/data/dataset-context";

type AuditLogRow = {
  audit_log_id: string;
  dataset_version_id?: string | null;
  calculation_run_id?: string | null;
  artifact_id?: string | null;
  actor_id?: string | null;
  actor_type?: string | null;
  action_type?: string | null;
  action_label?: string | null;
  created_at?: string | null;
  reason?: string | null;
  status?: string | null;
  error_message?: string | null;
};

export function InsightStream() {
  const { t } = useTranslation();
  const { datasetVersionId } = useDatasetContext();

  const query = useQuery({
    queryKey: ["audit-stream", datasetVersionId],
    enabled: Boolean(datasetVersionId),
    staleTime: 10_000,
    retry: false,
    queryFn: async () => {
      const data = await api.getAuditLogs({
        dataset_version_id: datasetVersionId || undefined,
        limit: 20,
        offset: 0,
      });
      return (data.logs || []) as AuditLogRow[];
    },
  });

  if (!datasetVersionId) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">
          {t("datasets.required", { defaultValue: "Select a dataset to view audit activity." })}
        </p>
      </div>
    );
  }

  if (query.isLoading) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-3)]">
        {t("states.loading", { defaultValue: "Loading..." })}
      </div>
    );
  }

  if (query.isError) {
    const message = (() => {
      if (query.error instanceof ApiError) {
        if (query.error.status === 401 || query.error.status === 403) {
          return t("datasets.restricted", {
            defaultValue: "Audit logs are restricted. Check your API key or permissions.",
          });
        }
        if (query.error.status >= 500) {
          return t("datasets.unavailable", {
            defaultValue:
              "Audit logs are unavailable (backend error). If running locally, configure the database connection.",
          });
        }
      }
      return t("states.error");
    })();
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">{t("states.error")}</p>
        <p className="mt-2 text-[var(--ink-3)]">{message}</p>
      </div>
    );
  }

  const logs = query.data || [];
  if (!logs.length) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">
          {t("dashboard.auditEmpty", { defaultValue: "No audit events found for this dataset." })}
        </p>
        <p className="mt-2 text-[var(--ink-3)]">
          {t("dashboard.auditEmptyBody", { defaultValue: "Run an engine to create audit entries." })}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.slice(0, 10).map((log) => (
        <div
          key={log.audit_log_id}
          className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
        >
          <div className="flex items-center justify-between gap-3 text-xs text-[var(--ink-3)]">
            <span className="font-semibold uppercase tracking-[0.2em]">
              {log.action_label || log.action_type || t("dashboard.auditEvent", { defaultValue: "Audit event" })}
            </span>
            <span>
              {log.created_at ? new Date(log.created_at).toLocaleString() : "--"}
            </span>
          </div>
          <div className="mt-2 text-sm text-[var(--ink-2)]">
            {log.reason || log.status || "--"}
          </div>
          {log.error_message ? (
            <div className="mt-2 rounded-xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-xs text-[var(--accent-error)]">
              {log.error_message}
            </div>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--ink-3)]">
            {log.calculation_run_id ? (
              <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1">
                run: {log.calculation_run_id.slice(0, 10)}
              </span>
            ) : null}
            {log.artifact_id ? (
              <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1">
                artifact: {log.artifact_id.slice(0, 10)}
              </span>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}
