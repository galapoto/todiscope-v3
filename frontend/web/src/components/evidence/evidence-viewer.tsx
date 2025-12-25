"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import type { Evidence, DocumentEvidence, StructuredRecordEvidence } from "./evidence-types";

type EvidenceViewerProps = {
  evidence: Evidence;
  onClose: () => void;
};

export function EvidenceViewer({ evidence, onClose }: EvidenceViewerProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"preview" | "ocr" | "metadata">("preview");

  if (evidence.type === "document") {
    return <DocumentViewer evidence={evidence} onClose={onClose} />;
  }

  return <StructuredRecordViewer evidence={evidence} onClose={onClose} />;
}

function DocumentViewer({
  evidence,
  onClose,
}: {
  evidence: DocumentEvidence;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"preview" | "ocr" | "metadata">("preview");
  const isImage = evidence.file_type?.startsWith("image/");
  const isPDF = evidence.file_type === "application/pdf";

  return (
    <Modal
      open={true}
      title={evidence.file_name || t("evidence.document")}
      onClose={onClose}
      size="lg"
    >
      <div className="flex flex-col gap-4">
        {/* Tabs */}
        <div className="flex gap-2 border-b border-[var(--surface-3)]">
          <button
            type="button"
            onClick={() => setActiveTab("preview")}
            className={`px-4 py-2 text-sm font-medium transition ${
              activeTab === "preview"
                ? "border-b-2 border-[var(--accent-1)] text-[var(--accent-1)]"
                : "text-[var(--ink-3)] hover:text-[var(--ink-2)]"
            }`}
          >
            {t("evidence.preview")}
          </button>
          {evidence.ocr_text && (
            <button
              type="button"
              onClick={() => setActiveTab("ocr")}
              className={`px-4 py-2 text-sm font-medium transition ${
                activeTab === "ocr"
                  ? "border-b-2 border-[var(--accent-1)] text-[var(--accent-1)]"
                  : "text-[var(--ink-3)] hover:text-[var(--ink-2)]"
              }`}
            >
              {t("evidence.ocrText")}
            </button>
          )}
          <button
            type="button"
            onClick={() => setActiveTab("metadata")}
            className={`px-4 py-2 text-sm font-medium transition ${
              activeTab === "metadata"
                ? "border-b-2 border-[var(--accent-1)] text-[var(--accent-1)]"
                : "text-[var(--ink-3)] hover:text-[var(--ink-2)]"
            }`}
          >
            {t("evidence.metadata")}
          </button>
        </div>

        {/* Content */}
        <div className="min-h-[400px]">
          {activeTab === "preview" && (
            <div className="flex items-center justify-center rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-8">
              {isImage && evidence.file_url ? (
                <img
                  src={evidence.file_url}
                  alt={evidence.file_name}
                  className="max-h-[500px] max-w-full rounded-lg object-contain"
                />
              ) : isPDF && evidence.file_url ? (
                <iframe
                  src={evidence.file_url}
                  className="h-[500px] w-full rounded-lg border border-[var(--surface-3)]"
                  title={evidence.file_name}
                />
              ) : (
                <div className="text-center text-[var(--ink-3)]">
                  <p className="mb-2">{t("evidence.noPreview")}</p>
                  {evidence.file_url && (
                    <Button
                      variant="secondary"
                      onClick={() => window.open(evidence.file_url, "_blank")}
                    >
                      {t("evidence.openFile")}
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === "ocr" && evidence.ocr_text && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--ink-2)]">
                    {t("evidence.ocrConfidence")}
                  </span>
                  <span
                    className={`text-sm font-semibold ${
                      (evidence.ocr_confidence || 0) > 0.8
                        ? "text-[var(--accent-success)]"
                        : (evidence.ocr_confidence || 0) > 0.5
                          ? "text-[var(--accent-warning)]"
                          : "text-[var(--accent-error)]"
                    }`}
                  >
                    {Math.round((evidence.ocr_confidence || 0) * 100)}%
                  </span>
                </div>
              </div>
              <div className="relative rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4">
                <pre className="whitespace-pre-wrap font-mono text-sm text-[var(--ink-2)]">
                  {evidence.ocr_text}
                </pre>
                {evidence.ocr_low_confidence_sections &&
                  evidence.ocr_low_confidence_sections.length > 0 && (
                    <div className="mt-4 rounded-lg border border-[var(--accent-warning)] bg-[var(--accent-warning)]/10 p-3">
                      <p className="text-xs font-semibold text-[var(--accent-warning)]">
                        {t("evidence.lowConfidenceSections")}
                      </p>
                      <ul className="mt-2 space-y-1 text-xs text-[var(--ink-3)]">
                        {evidence.ocr_low_confidence_sections.map((section, idx) => (
                          <li key={idx}>
                            {t("evidence.section")} {idx + 1}: {section.confidence * 100}%
                            {t("evidence.confidence")}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
              </div>
            </div>
          )}

          {activeTab === "metadata" && (
            <div className="space-y-3 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
              <MetadataRow label={t("evidence.sourceEngine")} value={evidence.source_engine} />
              <MetadataRow
                label={t("evidence.timestamp")}
                value={new Date(evidence.timestamp).toLocaleString()}
              />
              {evidence.hash && (
                <MetadataRow label={t("evidence.hash")} value={evidence.hash} />
              )}
              {evidence.checksum && (
                <MetadataRow label={t("evidence.checksum")} value={evidence.checksum} />
              )}
              {evidence.workflow_state && (
                <MetadataRow
                  label={t("evidence.workflowState")}
                  value={evidence.workflow_state}
                />
              )}
              {evidence.file_size && (
                <MetadataRow
                  label={t("evidence.fileSize")}
                  value={`${(evidence.file_size / 1024).toFixed(2)} KB`}
                />
              )}
              <MetadataRow
                label={t("evidence.status")}
                value={
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-semibold ${
                      evidence.status === "verified"
                        ? "bg-[var(--accent-success)]/15 text-[var(--accent-success)]"
                        : evidence.status === "pending"
                          ? "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]"
                          : "bg-[var(--accent-error)]/15 text-[var(--accent-error)]"
                    }`}
                  >
                    {t(`evidence.status.${evidence.status}`)}
                  </span>
                }
              />
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

function StructuredRecordViewer({
  evidence,
  onClose,
}: {
  evidence: StructuredRecordEvidence;
  onClose: () => void;
}) {
  const { t } = useTranslation();

  return (
    <Modal
      open={true}
      title={`${t("evidence.record")}: ${evidence.record_type}`}
      onClose={onClose}
      size="lg"
    >
      <div className="space-y-4">
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
          <h4 className="mb-3 text-sm font-semibold text-[var(--ink-1)]">
            {t("evidence.recordData")}
          </h4>
          <pre className="max-h-[400px] overflow-auto rounded-lg border border-[var(--surface-3)] bg-[var(--surface-1)] p-4 font-mono text-xs text-[var(--ink-2)]">
            {JSON.stringify(evidence.data, null, 2)}
          </pre>
        </div>
        <div className="space-y-2 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
          <MetadataRow label={t("evidence.sourceEngine")} value={evidence.source_engine} />
          <MetadataRow
            label={t("evidence.timestamp")}
            value={new Date(evidence.timestamp).toLocaleString()}
          />
          {evidence.source_table && (
            <MetadataRow label={t("evidence.sourceTable")} value={evidence.source_table} />
          )}
          {evidence.source_row_id && (
            <MetadataRow label={t("evidence.sourceRowId")} value={evidence.source_row_id} />
          )}
          <MetadataRow
            label={t("evidence.status")}
            value={
              <span
                className={`rounded-full px-2 py-1 text-xs font-semibold ${
                  evidence.status === "verified"
                    ? "bg-[var(--accent-success)]/15 text-[var(--accent-success)]"
                    : evidence.status === "pending"
                      ? "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]"
                      : "bg-[var(--accent-error)]/15 text-[var(--accent-error)]"
                }`}
              >
                {t(`evidence.status.${evidence.status}`)}
              </span>
            }
          />
        </div>
      </div>
    </Modal>
  );
}

function MetadataRow({
  label,
  value,
}: {
  label: string;
  value: string | React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-sm font-medium text-[var(--ink-3)]">{label}</span>
      <span className="text-right text-sm text-[var(--ink-2)]">{value}</span>
    </div>
  );
}



