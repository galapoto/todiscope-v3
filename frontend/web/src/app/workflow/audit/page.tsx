"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export default function AuditPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("workflow.audit.title", { defaultValue: "Audit Logs" })}
        subtitle={t("workflow.audit.subtitle", { defaultValue: "View audit trail and compliance logs" })}
      >
        <AuditWorkflow />
      </AppShell>
    </AuthGuard>
  );
}

function AuditWorkflow() {
  const { t } = useTranslation();
  const params = useSearchParams();
  const datasetVersionId = params.get("dataset_version_id") || "";
  const engineId = params.get("engine_id") || "";
  const [logs, setLogs] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getAuditLogs({
        dataset_version_id: datasetVersionId || undefined,
        // Fetch full audit trail for lineage (import → normalize → calculate → report).
        limit: 1000,
        offset: 0,
      });
      setLogs(response.logs || []);
      setTotal((response as { total?: number }).total || response.logs?.length || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.audit.loadFailed", { defaultValue: "Failed to load audit logs" })));
    } finally {
      setLoading(false);
    }
  }, [datasetVersionId, t]);

  useEffect(() => {
    if (datasetVersionId) {
      void loadLogs();
    }
  }, [datasetVersionId, loadLogs]);

  const handleExport = async (format: "csv" | "json") => {
    try {
      const blob = await api.exportAuditLogs({
        dataset_version_id: datasetVersionId || undefined,
        format,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_logs.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.audit.exportFailed", { defaultValue: "Export failed" })));
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[var(--ink-1)]">
            {t("workflow.audit.title", { defaultValue: "Audit Logs" })}
          </h3>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => handleExport("csv")}>
              {t("workflow.audit.exportCsv", { defaultValue: "Export CSV" })}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => handleExport("json")}>
              {t("workflow.audit.exportJson", { defaultValue: "Export JSON" })}
            </Button>
          </div>
        </div>
        <div className="mb-4 space-y-2 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
          {datasetVersionId && (
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.audit.datasetId", { defaultValue: "Dataset Version ID" })}:</span>{" "}
              <code className="font-mono text-xs">{datasetVersionId}</code>
            </p>
          )}
          {engineId && (
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.audit.engineId", { defaultValue: "Engine" })}:</span> {engineId}
            </p>
          )}
          <div className="mt-3 rounded border border-[var(--surface-3)] bg-[var(--surface-1)] p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
              {t("workflow.audit.lineage", { defaultValue: "Data Lineage" })}
            </p>
            <div className="mt-2 space-y-1 text-xs text-[var(--ink-3)]">
              <p>Import → Normalize → Calculate → Report → Audit</p>
              <p className="mt-2">
                {t("workflow.audit.lineageDescription", {
                  defaultValue: "Full traceability from data ingestion through report generation.",
                })}
              </p>
            </div>
          </div>
        </div>
        {error && (
          <div className="mb-4 rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
            {error}
          </div>
        )}
        {loading ? (
          <div className="py-8 text-center text-sm text-[var(--ink-3)]">
            {t("workflow.audit.loading", { defaultValue: "Loading audit logs..." })}
          </div>
        ) : logs.length === 0 ? (
          <div className="py-8 text-center text-sm text-[var(--ink-3)]">
            {t("workflow.audit.noLogs", { defaultValue: "No audit logs found" })}
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-[var(--ink-3)]">
              {t("workflow.audit.total", {
                count: total,
                defaultValue: "Total: {{count}} log(s)",
              })}
            </p>
            <div className="max-h-96 space-y-2 overflow-y-auto">
              {logs.map((log, idx) => (
                <div key={idx} className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
                  <pre className="text-xs">{JSON.stringify(log, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
