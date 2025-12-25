"use client";

import { useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { AlertCircle, CheckCircle2, XCircle, Eye, EyeOff, Edit2 } from "lucide-react";

type PreviewRecord = {
  raw_record_id: string;
  source_system: string;
  source_record_id: string;
  raw_payload: Record<string, unknown>;
  normalized_payload: Record<string, unknown>;
};

type NormalizationWarning = {
  raw_record_id: string;
  code: string;
  message: string;
  severity: "info" | "warning" | "error" | "critical";
  affected_fields?: string[];
  explanation?: string;
  recommendation?: string;
  confidence?: number;
};

type PreviewData = {
  dataset_version_id: string;
  total_records: number;
  preview_records: PreviewRecord[];
  warnings: NormalizationWarning[];
  warnings_by_severity: Record<string, number>;
};

type MappingProposal = {
  raw_field: string;
  suggested_field: string;
  confidence: number;
  data_type: string;
  sample_values: string[];
  approved?: boolean;
  custom_mapping?: string;
};

export default function NormalizePage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("workflow.normalize.title", { defaultValue: "Normalize Data" })}
        subtitle={t("workflow.normalize.subtitle", { defaultValue: "Normalize and validate dataset" })}
      >
        <NormalizeWorkflow />
      </AppShell>
    </AuthGuard>
  );
}

function NormalizeWorkflow() {
  const { t } = useTranslation();
  const router = useRouter();
  const params = useSearchParams();
  const engineId = params.get("engine_id") || "";
  const datasetVersionId = params.get("dataset_version_id") || "";
  const [previewing, setPreviewing] = useState(false);
  const [validating, setValidating] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [validation, setValidation] = useState<{ is_valid: boolean; warnings: NormalizationWarning[] } | null>(null);
  const [result, setResult] = useState<{ normalized_dataset_version_id: string; records_normalized: number; records_skipped: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRawData, setShowRawData] = useState(true);
  const [selectedRecordIndex, setSelectedRecordIndex] = useState<number | null>(null);
  const [mappingProposals, setMappingProposals] = useState<MappingProposal[]>([]);
  const [editingField, setEditingField] = useState<{ proposalIndex: number; field: "raw" | "suggested" } | null>(null);
  const [editingRecord, setEditingRecord] = useState<{ recordIndex: number; field: string; isRaw: boolean } | null>(null);

  const handlePreview = async () => {
    if (!datasetVersionId) {
      setError(String(t("workflow.normalize.noDataset", { defaultValue: "Dataset version ID required" })));
      return;
    }
    setPreviewing(true);
    setError(null);
    try {
      const data = await api.previewNormalization(datasetVersionId, 50);
      setPreview(data as PreviewData);
      
      // Generate mapping proposals from preview data
      if (data && typeof data === "object" && "preview_records" in data) {
        const records = (data as PreviewData).preview_records;
        if (records && records.length > 0) {
          const proposals = generateMappingProposals(records);
          setMappingProposals(proposals);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.normalize.previewFailed", { defaultValue: "Preview failed" })));
    } finally {
      setPreviewing(false);
    }
  };

  const generateMappingProposals = (records: PreviewRecord[]): MappingProposal[] => {
    const proposals: MappingProposal[] = [];
    const allRawFields = new Set<string>();
    
    records.forEach((record) => {
      Object.keys(record.raw_payload).forEach((key) => allRawFields.add(key));
    });

    allRawFields.forEach((rawField) => {
      const normalizedField = Object.keys(records[0]?.normalized_payload || {}).find(
        (normKey) => normKey.toLowerCase().includes(rawField.toLowerCase().slice(0, 3))
      ) || rawField.toLowerCase().replace(/[^a-z0-9]/g, "_");

      const sampleValues = records
        .slice(0, 5)
        .map((r) => String(r.raw_payload[rawField] || ""))
        .filter((v) => v.length > 0);

      const firstValue = sampleValues[0] || "";
      let dataType = "string";
      if (!isNaN(Number(firstValue)) && firstValue !== "") {
        dataType = "number";
      } else if (firstValue.match(/^\d{4}-\d{2}-\d{2}/)) {
        dataType = "date";
      }

      proposals.push({
        raw_field: rawField,
        suggested_field: normalizedField,
        confidence: 0.85,
        data_type: dataType,
        sample_values: sampleValues.slice(0, 3),
        approved: false,
      });
    });

    return proposals;
  };

  const handleValidate = async () => {
    if (!datasetVersionId) {
      setError(String(t("workflow.normalize.noDataset", { defaultValue: "Dataset version ID required" })));
      return;
    }
    setValidating(true);
    setError(null);
    try {
      const data = await api.validateNormalization(datasetVersionId);
      setValidation(data as { is_valid: boolean; warnings: NormalizationWarning[] });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(t("workflow.normalize.validateFailed", { defaultValue: "Validation failed" })));
    } finally {
      setValidating(false);
    }
  };

  const handleCommit = async () => {
    if (!datasetVersionId) {
      setError(String(t("workflow.normalize.noDataset", { defaultValue: "Dataset version ID required" })));
      return;
    }
    setCommitting(true);
    setError(null);
    setResult(null); // Clear previous result
    try {
      const data = await api.commitNormalization(datasetVersionId);
      console.log("Commit response:", data);
      
      // Handle different response structures
      const normalizedId = 
        (data as { normalized_dataset_version_id?: string })?.normalized_dataset_version_id ||
        (data as { source_dataset_version_id?: string })?.source_dataset_version_id ||
        datasetVersionId;
      
      const recordsNormalized = 
        (data as { records_normalized?: number })?.records_normalized || 0;
      
      const recordsSkipped = 
        (data as { records_skipped?: number })?.records_skipped || 0;
      
      const commitResult = {
        normalized_dataset_version_id: normalizedId,
        records_normalized: recordsNormalized,
        records_skipped: recordsSkipped,
      };
      
      console.log("Setting result:", commitResult);
      setResult(commitResult);
    } catch (err) {
      console.error("Commit error:", err);
      setError(err instanceof Error ? err.message : String(t("workflow.normalize.commitFailed", { defaultValue: "Commit failed" })));
    } finally {
      setCommitting(false);
    }
  };

  const handleContinue = () => {
    if (!result && !datasetVersionId) {
      console.error("Cannot continue: no result and no dataset version ID");
      setError(t("workflow.normalize.cannotContinue", { defaultValue: "Cannot continue: normalization result is missing." }));
      return;
    }
    const nextDatasetId = result?.normalized_dataset_version_id || datasetVersionId;
    const nextUrl = engineId
      ? `/workflow/calculate?dataset_version_id=${nextDatasetId}&engine_id=${engineId}`
      : `/workflow/calculate?dataset_version_id=${nextDatasetId}`;
    console.log("Navigating to:", nextUrl, { result, datasetVersionId, engineId, nextDatasetId });
    router.push(nextUrl);
  };

  const handleApproveMapping = (index: number) => {
    setMappingProposals((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], approved: true };
      return updated;
    });
  };

  const handleRejectMapping = (index: number) => {
    setMappingProposals((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], approved: false };
      return updated;
    });
  };

  const handleEditMapping = (index: number, field: "raw" | "suggested", value: string) => {
    setMappingProposals((prev) => {
      const updated = [...prev];
      if (field === "suggested") {
        updated[index] = { ...updated[index], suggested_field: value, custom_mapping: value };
      } else {
        updated[index] = { ...updated[index], raw_field: value };
      }
      return updated;
    });
  };

  const handleEditRecordField = (recordIndex: number, field: string, isRaw: boolean, value: unknown) => {
    if (!preview) return;
    setPreview((prev) => {
      if (!prev) return prev;
      const updated = { ...prev };
      const record = { ...updated.preview_records[recordIndex] };
      if (isRaw) {
        record.raw_payload = { ...record.raw_payload, [field]: value };
      } else {
        record.normalized_payload = { ...record.normalized_payload, [field]: value };
      }
      updated.preview_records[recordIndex] = record;
      return updated;
    });
  };

  // Table columns for row-by-row inspection
  const inspectionColumns = useMemo<ColumnDef<PreviewRecord>[]>(() => {
    if (!preview?.preview_records.length) return [];

    const rawKeys = Object.keys(preview.preview_records[0].raw_payload);
    const normalizedKeys = Object.keys(preview.preview_records[0].normalized_payload);

    return [
      {
        accessorKey: "source_record_id",
        header: () => t("workflow.normalize.inspection.recordId", { defaultValue: "Record ID" }),
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue()).slice(0, 12)}</span>
        ),
      },
      ...(showRawData
        ? rawKeys.slice(0, 5).map((key) => ({
            id: `raw_${key}`,
            header: () => (
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--ink-3)]">{key}</span>
                <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] text-blue-600 dark:text-blue-400">
                  {t("workflow.normalize.inspection.raw", { defaultValue: "Raw" })}
                </span>
              </div>
            ),
            cell: ({ row }: { row: { original: PreviewRecord; index: number } }) => {
              const value = row.original.raw_payload[key];
              const isEditing = editingRecord?.recordIndex === row.index && editingRecord?.field === key && editingRecord?.isRaw;
              return (
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <input
                      type="text"
                      defaultValue={String(value || "")}
                      onBlur={(e) => {
                        handleEditRecordField(row.index, key, true, e.target.value);
                        setEditingRecord(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleEditRecordField(row.index, key, true, (e.target as HTMLInputElement).value);
                          setEditingRecord(null);
                        } else if (e.key === "Escape") {
                          setEditingRecord(null);
                        }
                      }}
                      className="w-full rounded border border-[var(--accent-1)] bg-[var(--surface-1)] px-2 py-1 text-xs"
                      autoFocus
                    />
                  ) : (
                    <>
                      <span className="text-xs text-[var(--ink-2)]">
                        {typeof value === "object" ? JSON.stringify(value) : String(value || "")}
                      </span>
                      <button
                        onClick={() => setEditingRecord({ recordIndex: row.index, field: key, isRaw: true })}
                        className="opacity-0 group-hover:opacity-100 transition"
                        title={t("workflow.normalize.edit", { defaultValue: "Edit" })}
                      >
                        <Edit2 className="h-3 w-3 text-[var(--ink-3)]" />
                      </button>
                    </>
                  )}
                </div>
              );
            },
          }))
        : []),
      ...normalizedKeys.slice(0, 5).map((key) => ({
        id: `normalized_${key}`,
        header: () => (
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--ink-3)]">{key}</span>
            <span className="rounded bg-green-500/20 px-1.5 py-0.5 text-[10px] text-green-600 dark:text-green-400">
              {t("workflow.normalize.inspection.normalized", { defaultValue: "Normalized" })}
            </span>
          </div>
        ),
        cell: ({ row }: { row: { original: PreviewRecord; index: number } }) => {
          const value = row.original.normalized_payload[key];
          const isEditing = editingRecord?.recordIndex === row.index && editingRecord?.field === key && !editingRecord?.isRaw;
          return (
            <div className="flex items-center gap-2">
              {isEditing ? (
                <input
                  type="text"
                  defaultValue={String(value || "")}
                  onBlur={(e) => {
                    handleEditRecordField(row.index, key, false, e.target.value);
                    setEditingRecord(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleEditRecordField(row.index, key, false, (e.target as HTMLInputElement).value);
                      setEditingRecord(null);
                    } else if (e.key === "Escape") {
                      setEditingRecord(null);
                    }
                  }}
                  className="w-full rounded border border-[var(--accent-1)] bg-[var(--surface-1)] px-2 py-1 text-xs font-medium"
                  autoFocus
                />
              ) : (
                <>
                  <span className="text-xs text-[var(--ink-1)] font-medium">
                    {typeof value === "object" ? JSON.stringify(value) : String(value || "")}
                  </span>
                  <button
                    onClick={() => setEditingRecord({ recordIndex: row.index, field: key, isRaw: false })}
                    className="opacity-0 group-hover:opacity-100 transition"
                    title={t("workflow.normalize.edit", { defaultValue: "Edit" })}
                  >
                    <Edit2 className="h-3 w-3 text-[var(--ink-3)]" />
                  </button>
                </>
              )}
            </div>
          );
        },
      })),
    ] as ColumnDef<PreviewRecord>[];
  }, [preview, showRawData, editingRecord, t]);

  const inspectionTable = useReactTable({
    data: preview?.preview_records || [],
    columns: inspectionColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-6">
      {/* Dataset Info & Actions */}
      {datasetVersionId && (
        <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
          <div className="mb-4 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
            <p className="text-sm text-[var(--ink-2)]">
              <span className="font-medium">{t("workflow.normalize.datasetId", { defaultValue: "Dataset Version ID" })}:</span>{" "}
              <code className="font-mono text-xs">{datasetVersionId}</code>
            </p>
          </div>
          {error && (
            <div className="mb-4 rounded-lg border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
              {error}
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={handlePreview} loading={previewing} disabled={!datasetVersionId}>
              {t("workflow.normalize.preview", { defaultValue: "Preview Normalization" })}
            </Button>
            <Button variant="secondary" onClick={handleValidate} loading={validating} disabled={!datasetVersionId || !preview}>
              {t("workflow.normalize.validate", { defaultValue: "Validate" })}
            </Button>
            <Button variant="primary" onClick={handleCommit} loading={committing} disabled={!datasetVersionId || !preview}>
              {t("workflow.normalize.commit", { defaultValue: "Apply Mapping & Normalize" })}
            </Button>
          </div>
        </div>
      )}

      {/* Mapping Proposals - V2 Feature */}
      {mappingProposals.length > 0 && (
        <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
          <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
            {t("workflow.normalize.mappingProposals", { defaultValue: "Field Mapping Proposals" })}
          </h3>
          <p className="mb-4 text-sm text-[var(--ink-3)]">
            {t("workflow.normalize.mappingProposalsDesc", {
              defaultValue: "Review and approve suggested field mappings. Click to edit, approve, or reject. Confidence levels indicate mapping quality.",
            })}
          </p>
          <div className="space-y-2">
            {mappingProposals.map((proposal, idx) => {
              const isEditingRaw = editingField?.proposalIndex === idx && editingField?.field === "raw";
              const isEditingSuggested = editingField?.proposalIndex === idx && editingField?.field === "suggested";
              
              return (
                <div
                  key={idx}
                  className={`flex items-center justify-between rounded-xl border p-4 transition ${
                    proposal.approved
                      ? "border-[var(--accent-success)]/40 bg-[var(--accent-success)]/5"
                      : "border-[var(--surface-3)] bg-[var(--surface-2)]"
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      {isEditingRaw ? (
                        <input
                          type="text"
                          defaultValue={proposal.raw_field}
                          onBlur={(e) => {
                            handleEditMapping(idx, "raw", e.target.value);
                            setEditingField(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleEditMapping(idx, "raw", (e.target as HTMLInputElement).value);
                              setEditingField(null);
                            } else if (e.key === "Escape") {
                              setEditingField(null);
                            }
                          }}
                          className="rounded border border-[var(--accent-1)] bg-[var(--surface-1)] px-2 py-1 font-mono text-sm"
                          autoFocus
                        />
                      ) : (
                        <button
                          onClick={() => setEditingField({ proposalIndex: idx, field: "raw" })}
                          className="font-mono text-sm text-[var(--ink-1)] hover:text-[var(--accent-1)] transition flex items-center gap-1"
                        >
                          {proposal.raw_field}
                          <Edit2 className="h-3 w-3" />
                        </button>
                      )}
                      <span className="text-[var(--ink-3)]">→</span>
                      {isEditingSuggested ? (
                        <input
                          type="text"
                          defaultValue={proposal.suggested_field}
                          onBlur={(e) => {
                            handleEditMapping(idx, "suggested", e.target.value);
                            setEditingField(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleEditMapping(idx, "suggested", (e.target as HTMLInputElement).value);
                              setEditingField(null);
                            } else if (e.key === "Escape") {
                              setEditingField(null);
                            }
                          }}
                          className="rounded border border-[var(--accent-1)] bg-[var(--surface-1)] px-2 py-1 font-mono text-sm font-semibold"
                          autoFocus
                        />
                      ) : (
                        <button
                          onClick={() => setEditingField({ proposalIndex: idx, field: "suggested" })}
                          className="font-mono text-sm font-semibold text-[var(--accent-1)] hover:text-[var(--accent-1)]/80 transition flex items-center gap-1"
                        >
                          {proposal.suggested_field}
                          <Edit2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-xs text-[var(--ink-3)]">
                      <span>
                        {t("workflow.normalize.mapping.confidence", { defaultValue: "Confidence" })}:{" "}
                        <span className="font-semibold text-[var(--ink-1)]">{Math.round(proposal.confidence * 100)}%</span>
                      </span>
                      <span>
                        {t("workflow.normalize.mapping.dataType", { defaultValue: "Type" })}: {proposal.data_type}
                      </span>
                      {proposal.sample_values.length > 0 && (
                        <span>
                          {t("workflow.normalize.mapping.samples", { defaultValue: "Samples" })}:{" "}
                          {proposal.sample_values.slice(0, 2).join(", ")}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant={proposal.approved ? "primary" : "ghost"}
                      size="sm"
                      onClick={() => handleApproveMapping(idx)}
                    >
                      {t("workflow.normalize.mapping.approve", { defaultValue: "Approve" })}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRejectMapping(idx)}
                    >
                      {t("workflow.normalize.mapping.reject", { defaultValue: "Reject" })}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Row-by-Row Inspection - V2 Feature */}
      {preview && preview.preview_records.length > 0 && (
        <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-[var(--ink-1)]">
                {t("workflow.normalize.inspection.title", { defaultValue: "Row-by-Row Data Inspection" })}
              </h3>
              <p className="mt-1 text-sm text-[var(--ink-3)]">
                {t("workflow.normalize.inspection.desc", {
                  defaultValue: "Inspect and modify normalized data before committing. Click any field to edit. Toggle to view raw vs normalized side-by-side.",
                })}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRawData(!showRawData)}
              className="flex items-center gap-2"
            >
              {showRawData ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showRawData
                ? t("workflow.normalize.inspection.hideRaw", { defaultValue: "Hide Raw" })
                : t("workflow.normalize.inspection.showRaw", { defaultValue: "Show Raw" })}
            </Button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)]">
            <table className="w-full">
              <thead className="border-b border-[var(--surface-3)] bg-[var(--surface-1)]">
                {inspectionTable.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.1em] text-[var(--ink-3)]"
                      >
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {inspectionTable.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className={`group border-b border-[var(--surface-3)] transition hover:bg-[var(--surface-1)] ${
                      selectedRecordIndex === row.index ? "bg-[var(--accent-1)]/10" : ""
                    }`}
                    onClick={() => setSelectedRecordIndex(row.index === selectedRecordIndex ? null : row.index)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-[var(--ink-3)]">
            {t("workflow.normalize.inspection.totalRecords", {
              defaultValue: "Showing {{count}} of {{total}} records",
              count: preview.preview_records.length,
              total: preview.total_records,
            })}
          </p>
        </div>
      )}

      {/* Warnings Display - V2 Feature */}
      {preview && preview.warnings.length > 0 && (
        <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
          <h3 className="mb-4 text-lg font-semibold text-[var(--ink-1)]">
            {t("workflow.normalize.warnings.title", { defaultValue: "Normalization Warnings" })}
          </h3>
          <div className="space-y-2">
            {preview.warnings.slice(0, 10).map((warning, idx) => {
              const Icon =
                warning.severity === "critical" || warning.severity === "error"
                  ? XCircle
                  : warning.severity === "warning"
                    ? AlertCircle
                    : CheckCircle2;
              const colorClass =
                warning.severity === "critical" || warning.severity === "error"
                  ? "text-[var(--accent-error)]"
                  : warning.severity === "warning"
                    ? "text-[var(--accent-warning)]"
                    : "text-[var(--accent-success)]";
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3 rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
                >
                  <Icon className={`h-5 w-5 flex-shrink-0 ${colorClass}`} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[var(--ink-1)]">{warning.message}</p>
                    {warning.explanation && (
                      <p className="mt-1 text-xs text-[var(--ink-3)]">{warning.explanation}</p>
                    )}
                    {warning.recommendation && (
                      <p className="mt-1 text-xs text-[var(--ink-2)]">
                        <span className="font-semibold">
                          {t("workflow.normalize.warnings.recommendation", { defaultValue: "Recommendation" })}:
                        </span>{" "}
                        {warning.recommendation}
                      </p>
                    )}
                    {warning.affected_fields && warning.affected_fields.length > 0 && (
                      <p className="mt-1 text-xs text-[var(--ink-3)]">
                        {t("workflow.normalize.warnings.affectedFields", { defaultValue: "Affected fields" })}:{" "}
                        {warning.affected_fields.join(", ")}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {preview.warnings.length > 10 && (
            <p className="mt-4 text-xs text-[var(--ink-3)]">
              {t("workflow.normalize.warnings.more", {
                defaultValue: "And {{count}} more warnings...",
                count: preview.warnings.length - 10,
              })}
            </p>
          )}
        </div>
      )}

      {/* Validation Results */}
      {validation && (
        <div
          className={`rounded-lg border p-4 ${
            validation.is_valid
              ? "border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 text-[var(--accent-success)]"
              : "border-[var(--accent-warning)]/40 bg-[var(--accent-warning)]/10 text-[var(--accent-warning)]"
          }`}
        >
          <p className="text-sm font-medium">
            {validation.is_valid
              ? t("workflow.normalize.validationPassed", { defaultValue: "Validation passed" })
              : t("workflow.normalize.validationFailed", { defaultValue: "Validation failed" })}
          </p>
          {validation.warnings.length > 0 && (
            <p className="mt-2 text-xs">
              {t("workflow.normalize.warnings", {
                count: validation.warnings.length,
                defaultValue: "{{count}} warning(s)",
              })}
            </p>
          )}
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="rounded-3xl border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-[var(--accent-success)]">
              {t("workflow.normalize.successTitle", { defaultValue: "Normalization Complete" })}
            </h3>
            <p className="mt-2 text-sm text-[var(--accent-success)]">
              {t("workflow.normalize.success", {
                defaultValue: "Normalization successful! Normalized {{count}} records.",
                count: result.records_normalized || 0,
              })}
            </p>
            {result.records_skipped > 0 && (
              <p className="mt-2 text-sm text-[var(--accent-warning)]">
                {t("workflow.normalize.skipped", {
                  defaultValue: "Skipped {{count}} records due to errors.",
                  count: result.records_skipped,
                })}
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={handleContinue}>
              {t("workflow.normalize.continue", { defaultValue: "Continue to Calculate" })}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
