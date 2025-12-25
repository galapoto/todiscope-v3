"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
export default function ImportPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("workflow.import.title", { defaultValue: "Import Data" })}
        subtitle={t("workflow.import.subtitle", { defaultValue: "Upload and ingest datasets" })}
      >
        <ImportWorkflow />
      </AppShell>
    </AuthGuard>
  );
}

function ImportWorkflow() {
  const { t } = useTranslation();
  const router = useRouter();
  const params = useSearchParams();
  const engineId = params.get("engine_id") || "";
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceSystem, setSourceSystem] = useState("");
  const [result, setResult] = useState<{
    dataset_version_id: string;
    import_id: string;
    raw_records_written?: number;
  } | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selected]);
    setError(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError(String(t("workflow.import.noFiles", { defaultValue: "Please select at least one file" })));
      return;
    }
    if (!sourceSystem.trim()) {
      setError(
        String(
          t("workflow.import.sourceSystemRequired", {
            defaultValue: "Source system is required to ingest this dataset",
          })
        )
      );
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const file = files[0]; // Start with first file
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.ingestFile(file, false, undefined, sourceSystem);
      setResult(response as { dataset_version_id: string; import_id: string; raw_records_written?: number });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.import.uploadFailed", { defaultValue: "Upload failed" })));
    } finally {
      setUploading(false);
    }
  };

  const handleContinue = () => {
    if (result?.dataset_version_id) {
      const nextUrl = engineId
        ? `/workflow/normalize?dataset_version_id=${result.dataset_version_id}&engine_id=${engineId}`
        : `/workflow/normalize?dataset_version_id=${result.dataset_version_id}`;
      router.push(nextUrl);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
        <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
          {t("workflow.import.uploadTitle", { defaultValue: "Upload Dataset" })}
        </h3>
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-[var(--ink-2)]">
              {t("workflow.import.selectFile", { defaultValue: "Select file (JSON, CSV, NDJSON)" })}
            </label>
            <input
              type="file"
              accept=".json,.csv,.ndjson"
              onChange={handleFileSelect}
              className="w-full rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--ink-1)]"
              disabled={uploading}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-[var(--ink-2)]">
              {t("workflow.import.sourceSystem", { defaultValue: "Source system" })}
            </label>
            <input
              type="text"
              value={sourceSystem}
              onChange={(e) => setSourceSystem(e.target.value)}
              placeholder={t("workflow.import.sourceSystemPlaceholder", { defaultValue: "e.g., erp, billing, ledger" })}
              className="w-full rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--ink-1)]"
              disabled={uploading}
            />
          </div>
          {files.length > 0 && (
            <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
              <p className="text-sm text-[var(--ink-2)]">
                {t("workflow.import.selectedFile", { defaultValue: "Selected:" })} {files[0].name}
              </p>
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
              {error}
            </div>
          )}
          {result && (
            <div className="rounded-lg border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 p-3 text-sm text-[var(--accent-success)]">
              <p>
                {t("workflow.import.success", {
                  defaultValue: "Import successful! Dataset Version ID: {{id}}",
                  id: result.dataset_version_id,
                })}
              </p>
              {result.raw_records_written && (
                <p className="mt-1">
                  {t("workflow.import.recordsWritten", {
                    count: result.raw_records_written,
                    defaultValue: "{{count}} records written",
                  })}
                </p>
              )}
            </div>
          )}
          <div className="flex gap-3">
            <Button variant="primary" onClick={handleUpload} loading={uploading} disabled={files.length === 0}>
              {t("workflow.import.upload", { defaultValue: "Upload" })}
            </Button>
            {result && (
              <Button variant="secondary" onClick={handleContinue}>
                {t("workflow.import.continue", { defaultValue: "Continue to Normalize" })}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
