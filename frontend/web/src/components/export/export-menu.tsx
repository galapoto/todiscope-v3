"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export type ExportFormat = "pdf" | "excel" | "csv";

export type ExportData = {
  title: string;
  content?: string;
  tables?: Array<{
    name: string;
    headers: string[];
    rows: (string | number)[][];
  }>;
  metadata?: Record<string, string>;
};

type ExportMenuProps = {
  data: ExportData;
  filename?: string;
  onExport?: (format: ExportFormat) => void;
};

export function ExportMenu({ data, filename, onExport }: ExportMenuProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async (format: ExportFormat) => {
    setIsExporting(true);
    setExportError(null);
    try {
      if (onExport) {
        await onExport(format);
      } else {
        await defaultExport(format);
      }
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      setExportError(message || t("states.error", { defaultValue: "Error" }));
    } finally {
      setIsExporting(false);
    }
  };

  const defaultExport = async (format: ExportFormat) => {
    const baseFilename = filename || `export-${new Date().toISOString().split("T")[0]}`;

    switch (format) {
      case "pdf":
        await exportPDF(data, baseFilename);
        break;
      case "excel":
        await exportExcel(data, baseFilename);
        break;
      case "csv":
        await exportCSV(data, baseFilename);
        break;
    }
  };

  return (
    <>
      <Button variant="secondary" size="sm" onClick={() => setIsOpen(true)}>
        {t("export.menu", { defaultValue: "Export" })} ↓
      </Button>
      {isOpen && (
        <Modal
          open={isOpen}
          title={t("export.title", { defaultValue: "Export Options" })}
          onClose={() => setIsOpen(false)}
          size="sm"
        >
          <div className="space-y-3">
            <p className="text-sm text-[var(--ink-2)]">
              {t("export.description", { defaultValue: "Choose export format:" })}
            </p>
            <div className="flex flex-col gap-2">
              <Button
                variant="primary"
                onClick={() => handleExport("pdf")}
                disabled={isExporting}
                className="w-full justify-start"
              >
                📄 {t("export.pdf", { defaultValue: "Export as PDF" })}
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleExport("excel")}
                disabled={isExporting}
                className="w-full justify-start"
              >
                📊 {t("export.excel", { defaultValue: "Export as Excel" })}
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleExport("csv")}
                disabled={isExporting}
                className="w-full justify-start"
              >
                📋 {t("export.csv", { defaultValue: "Export as CSV" })}
              </Button>
            </div>
            {isExporting && (
              <p className="text-xs text-[var(--ink-3)]">
                {t("export.processing", { defaultValue: "Processing..." })}
              </p>
            )}
            {exportError ? (
              <p className="rounded-xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
                {exportError}
              </p>
            ) : null}
          </div>
        </Modal>
      )}
    </>
  );
}

async function exportPDF(data: ExportData, filename: string) {
  const { default: jsPDF } = await import("jspdf");
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 14;
  let yPos = margin;

  // Title
  doc.setFontSize(16);
  doc.text(data.title, margin, yPos);
  yPos += 10;

  // Metadata
  if (data.metadata) {
    doc.setFontSize(10);
    Object.entries(data.metadata).forEach(([key, value]) => {
      doc.text(`${key}: ${value}`, margin, yPos);
      yPos += 6;
    });
    yPos += 5;
  }

  // Content
  if (data.content) {
    doc.setFontSize(12);
    const lines = doc.splitTextToSize(data.content, pageWidth - 2 * margin);
    lines.forEach((line: string) => {
      if (yPos > doc.internal.pageSize.getHeight() - 20) {
        doc.addPage();
        yPos = margin;
      }
      doc.text(line, margin, yPos);
      yPos += 6;
    });
    yPos += 5;
  }

  // Tables
  if (data.tables) {
    data.tables.forEach((table) => {
      if (yPos > doc.internal.pageSize.getHeight() - 40) {
        doc.addPage();
        yPos = margin;
      }

      doc.setFontSize(12);
      doc.text(table.name, margin, yPos);
      yPos += 8;

      // Simple table rendering (for complex tables, consider using a library)
      doc.setFontSize(10);
      const colWidth = (pageWidth - 2 * margin) / table.headers.length;
      table.headers.forEach((header, idx) => {
        doc.text(header, margin + idx * colWidth, yPos);
      });
      yPos += 6;

      table.rows.slice(0, 20).forEach((row) => {
        if (yPos > doc.internal.pageSize.getHeight() - 20) {
          doc.addPage();
          yPos = margin;
        }
        row.forEach((cell, idx) => {
          doc.text(String(cell), margin + idx * colWidth, yPos);
        });
        yPos += 6;
      });
      yPos += 10;
    });
  }

  doc.save(`${filename}.pdf`);
}

async function exportExcel(data: ExportData, filename: string) {
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();

  // Content sheet
  if (data.content || data.metadata) {
    const contentData: string[][] = [];
    if (data.metadata) {
      Object.entries(data.metadata).forEach(([key, value]) => {
        contentData.push([key, value]);
      });
      contentData.push([]);
    }
    if (data.content) {
      contentData.push([data.content]);
    }
    const ws = XLSX.utils.aoa_to_sheet(contentData);
    XLSX.utils.book_append_sheet(wb, ws, "Content");
  }

  // Table sheets
  if (data.tables) {
    data.tables.forEach((table) => {
      const tableData = [table.headers, ...table.rows];
      const ws = XLSX.utils.aoa_to_sheet(tableData);
      ws["!cols"] = table.headers.map(() => ({ wch: 20 }));
      XLSX.utils.book_append_sheet(wb, ws, table.name.substring(0, 31)); // Excel sheet name limit
    });
  }

  XLSX.writeFile(wb, `${filename}.xlsx`);
}

async function exportCSV(data: ExportData, filename: string) {
  let csvContent = "";

  // Metadata
  if (data.metadata) {
    Object.entries(data.metadata).forEach(([key, value]) => {
      csvContent += `${escapeCSV(key)},${escapeCSV(value)}\n`;
    });
    csvContent += "\n";
  }

  // Tables
  if (data.tables && data.tables.length > 0) {
    data.tables.forEach((table) => {
      csvContent += `${escapeCSV(table.name)}\n`;
      csvContent += table.headers.map(escapeCSV).join(",") + "\n";
      table.rows.forEach((row) => {
        csvContent += row.map(escapeCSV).join(",") + "\n";
      });
      csvContent += "\n";
    });
  } else if (data.content) {
    csvContent += escapeCSV(data.content);
  }

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeCSV(value: string | number): string {
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}
