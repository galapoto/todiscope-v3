"use client";

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { EvidenceViewer } from "@/components/evidence/evidence-viewer";
import { api } from "@/lib/api-client";
import type { DocumentEvidence } from "@/components/evidence/evidence-types";

export type OCRProcessingState = "idle" | "uploading" | "processing" | "completed" | "error";

export type OCRResult = {
  evidence: DocumentEvidence;
  extractedText: string;
  confidence: number;
  lowConfidenceSections?: Array<{
    start: number;
    end: number;
    confidence: number;
  }>;
};

type OCRUploadProps = {
  onUploadComplete?: (result: OCRResult) => void;
  onAttachToDataset?: (result: OCRResult, datasetId: string) => void;
  onAttachToEvidence?: (result: OCRResult, evidenceId: string) => void;
  onAttachToReport?: (result: OCRResult, reportId: string) => void;
  maxFileSize?: number; // in bytes
  acceptedFormats?: string[];
};

export function OCRUpload({
  onUploadComplete,
  onAttachToDataset,
  onAttachToEvidence,
  onAttachToReport,
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  acceptedFormats = ["application/pdf", "image/png", "image/jpeg", "image/jpg"],
}: OCRUploadProps) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<File[]>([]);
  const [processingState, setProcessingState] = useState<OCRProcessingState>("idle");
  const [results, setResults] = useState<OCRResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [previewEvidence, setPreviewEvidence] = useState<DocumentEvidence | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const droppedFiles = Array.from(e.dataTransfer.files);
      handleFiles(droppedFiles);
    },
    []
  );

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  }, []);

  const handleFiles = (newFiles: File[]) => {
    setError(null);
    const validFiles: File[] = [];

    for (const file of newFiles) {
      if (!acceptedFormats.includes(file.type)) {
        setError(t("ocr.invalidFormat", { file: file.name, defaultValue: `Invalid format for ${file.name}` }));
        continue;
      }
      if (file.size > maxFileSize) {
        setError(
          t("ocr.fileTooLarge", {
            file: file.name,
            maxSize: `${(maxFileSize / 1024 / 1024).toFixed(0)}MB`,
            defaultValue: `File ${file.name} is too large (max ${(maxFileSize / 1024 / 1024).toFixed(0)}MB)`,
          })
        );
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const processFiles = async () => {
    if (files.length === 0) return;

    setProcessingState("uploading");
    setError(null);

    try {
      const newResults: OCRResult[] = [];

      for (const file of files) {
        setProcessingState("processing");

        try {
          // Call real backend OCR API
          const uploadResult = await api.uploadOCR(file);
          
          // Transform backend response to OCRResult format
          const resultData = uploadResult as Record<string, unknown>;
          const evidenceData = resultData.evidence as Record<string, unknown>;
          
          const normalizedConfidence = (() => {
            const conf = evidenceData.ocr_confidence;
            if (typeof conf === "number") return conf;
            if (Array.isArray(conf)) {
              const first = conf.find((v) => typeof v === "number");
              return typeof first === "number" ? first : undefined;
            }
            return undefined;
          })();

          const lowConfidenceSections = Array.isArray(resultData.low_confidence_sections)
            ? (resultData.low_confidence_sections as OCRResult["lowConfidenceSections"])
            : undefined;

          const ocrResult: OCRResult = {
            evidence: {
              id: String(evidenceData.id ?? `evidence-${Date.now()}`),
              type: "document",
              status: (evidenceData.status as DocumentEvidence["status"]) ?? "pending",
              source_engine: String(evidenceData.source_engine ?? "ocr"),
              timestamp: String(evidenceData.timestamp ?? new Date().toISOString()),
              file_name: String(evidenceData.file_name ?? file.name),
              file_type: String(evidenceData.file_type ?? file.type),
              file_url: typeof evidenceData.file_url === "string" ? evidenceData.file_url : undefined,
              ocr_text: typeof evidenceData.ocr_text === "string" ? evidenceData.ocr_text : undefined,
              ocr_confidence: normalizedConfidence,
              ocr_low_confidence_sections: lowConfidenceSections,
            },
            extractedText: String(resultData.extracted_text ?? resultData.extractedText ?? ""),
            confidence: typeof resultData.confidence === "number" ? resultData.confidence : 0,
            lowConfidenceSections,
          };

          newResults.push(ocrResult);
          if (onUploadComplete) {
            onUploadComplete(ocrResult);
          }
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : t("ocr.processingError", { defaultValue: `Failed to process ${file.name}` })
          );
          setProcessingState("error");
          // Continue processing other files even if one fails
        }
      }

      setResults((prev) => [...prev, ...newResults]);
      setFiles([]);
      setProcessingState("completed");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("ocr.processingError", { defaultValue: "Failed to process files" })
      );
      setProcessingState("error");
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const getProcessingStatus = () => {
    switch (processingState) {
      case "uploading":
        return t("ocr.uploading", { defaultValue: "Uploading..." });
      case "processing":
        return t("ocr.processing", { defaultValue: "Processing..." });
      case "completed":
        return t("ocr.completed", { defaultValue: "Completed" });
      case "error":
        return t("ocr.error", { defaultValue: "Error" });
      default:
        return t("ocr.ready", { defaultValue: "Ready" });
    }
  };

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={`relative rounded-2xl border-2 border-dashed p-8 text-center transition ${
          processingState === "processing" || processingState === "uploading"
            ? "border-[var(--accent-1)] bg-[var(--accent-1)]/5"
            : "border-[var(--surface-3)] bg-[var(--surface-2)] hover:border-[var(--accent-1)]"
        }`}
      >
        <input
          type="file"
          id="ocr-upload"
          multiple
          accept={acceptedFormats.join(",")}
          onChange={handleFileInput}
          className="hidden"
          disabled={processingState === "processing" || processingState === "uploading"}
        />
        <label
          htmlFor="ocr-upload"
          className={`cursor-pointer ${processingState === "processing" || processingState === "uploading" ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <div className="mb-4 text-4xl">📄</div>
          <p className="mb-2 text-sm font-medium text-[var(--ink-1)]">
            {t("ocr.dropFiles", { defaultValue: "Drop files here or click to upload" })}
          </p>
          <p className="text-xs text-[var(--ink-3)]">
            {t("ocr.supportedFormats", {
              formats: acceptedFormats.map((f) => f.split("/")[1]).join(", "),
              maxSize: `${(maxFileSize / 1024 / 1024).toFixed(0)}MB`,
              defaultValue: `Supported: PDF, PNG, JPEG (max ${(maxFileSize / 1024 / 1024).toFixed(0)}MB)`,
            })}
          </p>
        </label>
        {processingState === "processing" && (
          <div className="mt-4 flex items-center justify-center gap-2">
            <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--accent-1)] [animation-delay:0ms]" />
            <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--accent-1)] [animation-delay:150ms]" />
            <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--accent-1)] [animation-delay:300ms]" />
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-lg border border-[var(--accent-error)] bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
          {error}
        </div>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-[var(--ink-1)]">
            {t("ocr.queuedFiles", { count: files.length, defaultValue: `${files.length} file(s) queued` })}
          </h4>
          <div className="space-y-2 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
            {files.map((file, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="text-[var(--ink-2)]">{file.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--ink-3)]">
                    {(file.size / 1024).toFixed(2)} KB
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(idx)}
                    className="text-[var(--accent-error)] hover:underline"
                  >
                    {t("ocr.remove", { defaultValue: "Remove" })}
                  </button>
                </div>
              </div>
            ))}
          </div>
          <Button
            variant="primary"
            onClick={processFiles}
            disabled={processingState === "processing" || processingState === "uploading"}
          >
            {t("ocr.process", { defaultValue: "Process Files" })}
          </Button>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-[var(--ink-1)]">
            {t("ocr.results", { count: results.length, defaultValue: `${results.length} result(s)` })}
          </h4>
          <div className="space-y-3">
            {results.map((result, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-[var(--ink-1)]">
                      {result.evidence.file_name}
                    </p>
                    <p className="text-xs text-[var(--ink-3)]">
                      {t("ocr.confidence", {
                        value: Math.round(result.confidence * 100),
                        defaultValue: `${Math.round(result.confidence * 100)}% confidence`,
                      })}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPreviewEvidence(result.evidence)}
                    >
                      {t("ocr.preview", { defaultValue: "Preview" })}
                    </Button>
                  </div>
                </div>
                {result.lowConfidenceSections && result.lowConfidenceSections.length > 0 && (
                  <div className="mt-2 rounded border border-[var(--accent-warning)] bg-[var(--accent-warning)]/10 p-2">
                    <p className="text-xs font-semibold text-[var(--accent-warning)]">
                      {t("ocr.lowConfidence", {
                        count: result.lowConfidenceSections.length,
                        defaultValue: `${result.lowConfidenceSections.length} low confidence section(s)`,
                      })}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewEvidence && (
        <EvidenceViewer
          evidence={previewEvidence}
          onClose={() => setPreviewEvidence(null)}
        />
      )}
    </div>
  );
}
