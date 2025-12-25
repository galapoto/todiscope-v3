"use client";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EvidenceViewer } from "@/components/evidence/evidence-viewer";
import { AuthGuard } from "@/components/auth/auth-guard";
import type { Evidence } from "@/components/evidence/evidence-types";

function coerceEvidence(evidenceId: string, data: unknown): Evidence {
  if (data && typeof data === "object") {
    const anyData = data as Record<string, unknown>;
    const type = anyData.type;
    if (type === "document") {
      return {
        id: String(anyData.id ?? evidenceId),
        type: "document",
        status: (anyData.status as Evidence["status"]) ?? "pending",
        source_engine: String(anyData.source_engine ?? "unknown"),
        timestamp: String(anyData.timestamp ?? new Date().toISOString()),
        file_name: String(anyData.file_name ?? "evidence"),
        file_type: String(anyData.file_type ?? "application/octet-stream"),
        file_url: typeof anyData.file_url === "string" ? anyData.file_url : undefined,
        ocr_text: typeof anyData.ocr_text === "string" ? anyData.ocr_text : undefined,
        workflow_state: typeof anyData.workflow_state === "string" ? anyData.workflow_state : undefined,
      };
    }
    if (type === "structured_record") {
      return {
        id: String(anyData.id ?? evidenceId),
        type: "structured_record",
        status: (anyData.status as Evidence["status"]) ?? "pending",
        source_engine: String(anyData.source_engine ?? "unknown"),
        timestamp: String(anyData.timestamp ?? new Date().toISOString()),
        record_type: String(anyData.record_type ?? "record"),
        data:
          anyData.data && typeof anyData.data === "object"
            ? (anyData.data as Record<string, unknown>)
            : {},
        workflow_state: typeof anyData.workflow_state === "string" ? anyData.workflow_state : undefined,
      };
    }
  }

  return {
    id: evidenceId,
    type: "structured_record",
    status: "pending",
    source_engine: "unknown",
    timestamp: new Date().toISOString(),
    record_type: "evidence",
    data: { raw: data },
  };
}

export default function EvidencePage() {
  const params = useParams<{ evidenceId: string }>();
  const evidenceId = params?.evidenceId ?? "";
  const { t } = useTranslation();
  const router = useRouter();
  const [open, setOpen] = useState(true);

  const evidenceQuery = useQuery({
    queryKey: ["evidence", evidenceId],
    enabled: Boolean(evidenceId),
    staleTime: 60_000,
    retry: false,
    queryFn: () => api.getEvidence(evidenceId),
  });

  const evidence = useMemo(() => {
    if (!evidenceId || !evidenceQuery.data) return null;
    return coerceEvidence(evidenceId, evidenceQuery.data);
  }, [evidenceId, evidenceQuery.data]);

  return (
    <AuthGuard>
      <AppShell
        title={t("evidence.title", { defaultValue: "Evidence" })}
        subtitle={t("evidence.subtitle", { defaultValue: "Evidence viewer" })}
      >
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("evidence.id", { defaultValue: "Evidence ID" })}
            </p>
            <p className="mt-2 font-mono text-sm text-[var(--ink-2)]">{evidenceId}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => router.back()}>
              {t("navigation.back", { defaultValue: "Back" })}
            </Button>
            <Button
              variant="primary"
              onClick={() => setOpen(true)}
              disabled={!evidence}
              loading={evidenceQuery.isLoading}
            >
              {t("evidence.open", { defaultValue: "Open viewer" })}
            </Button>
          </div>
        </div>

        {evidenceQuery.isError ? (
          <div className="mt-4 rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
            {t("evidence.loadFailed", { defaultValue: "Failed to load evidence from backend." })}
          </div>
        ) : evidenceQuery.isLoading ? (
          <div className="mt-4 text-sm text-[var(--ink-3)]">{t("states.loading")}</div>
        ) : evidence ? (
          <div className="mt-4 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-xs text-[var(--ink-3)]">
            {t("evidence.ready", { defaultValue: "Evidence loaded. Use “Open viewer” to inspect." })}
          </div>
        ) : (
          <div className="mt-4 text-sm text-[var(--ink-3)]">{t("states.empty")}</div>
        )}
      </div>

      {open && evidence ? (
        <EvidenceViewer
          evidence={evidence}
          onClose={() => {
            setOpen(false);
          }}
        />
      ) : null}
      </AppShell>
    </AuthGuard>
  );
}
