"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { EvidenceViewer } from "./evidence-viewer";
import type { Evidence } from "./evidence-types";

type EvidenceBadgeProps = {
  evidence: Evidence[];
  linkedTo?: string; // ID of the finding/metric/insight
  compact?: boolean;
};

export function EvidenceBadge({ evidence, linkedTo, compact = false }: EvidenceBadgeProps) {
  const { t } = useTranslation();
  const [viewingEvidence, setViewingEvidence] = useState<Evidence | null>(null);

  if (!evidence || evidence.length === 0) {
    return null;
  }

  const verifiedCount = evidence.filter((e) => e.status === "verified").length;
  const pendingCount = evidence.filter((e) => e.status === "pending").length;
  const disputedCount = evidence.filter((e) => e.status === "disputed").length;

  if (compact) {
    return (
      <>
        <button
          type="button"
          onClick={() => setViewingEvidence(evidence[0])}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-2 py-1 text-xs font-medium text-[var(--ink-2)] transition hover:border-[var(--accent-1)] hover:text-[var(--accent-1)]"
          aria-label={t("evidence.viewEvidence", { count: evidence.length })}
        >
          <span>📎</span>
          <span>{evidence.length}</span>
        </button>
        {viewingEvidence && (
          <EvidenceViewer
            evidence={viewingEvidence}
            onClose={() => setViewingEvidence(null)}
          />
        )}
      </>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setViewingEvidence(evidence[0])}
          className="inline-flex items-center gap-2 rounded-full border border-[var(--accent-1)] bg-[var(--accent-1)]/10 px-3 py-1.5 text-xs font-semibold text-[var(--accent-1)] transition hover:bg-[var(--accent-1)]/20"
        >
          <span>📎</span>
          <span>{t("evidence.viewEvidence")}</span>
          <span className="rounded-full bg-[var(--accent-1)]/20 px-2 py-0.5">
            {evidence.length}
          </span>
        </button>
        {verifiedCount > 0 && (
          <span className="rounded-full bg-[var(--accent-success)]/15 px-2 py-1 text-xs font-semibold text-[var(--accent-success)]">
            ✓ {verifiedCount} {t("evidence.verified")}
          </span>
        )}
        {pendingCount > 0 && (
          <span className="rounded-full bg-[var(--accent-warning)]/15 px-2 py-1 text-xs font-semibold text-[var(--accent-warning)]">
            ⏳ {pendingCount} {t("evidence.pending")}
          </span>
        )}
        {disputedCount > 0 && (
          <span className="rounded-full bg-[var(--accent-error)]/15 px-2 py-1 text-xs font-semibold text-[var(--accent-error)]">
            ⚠ {disputedCount} {t("evidence.disputed")}
          </span>
        )}
      </div>
      {viewingEvidence && (
        <EvidenceViewer evidence={viewingEvidence} onClose={() => setViewingEvidence(null)} />
      )}
    </>
  );
}



