"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { EvidenceBadge } from "@/components/evidence/evidence-badge";
import {
  WorkflowActions,
  type WorkflowAction,
  type WorkflowStatus,
} from "@/components/workflow/workflow-actions";
import { AIPanel, type AIContext } from "@/components/ai/ai-panel";
import { Modal } from "@/components/ui/modal";
import type { Evidence } from "@/components/evidence/evidence-types";

export type Finding = {
  id: string;
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  engine: string;
  evidence?: Evidence[];
  workflowStatus: WorkflowStatus;
  workflowHistory?: Array<{
    action: WorkflowAction;
    timestamp: string;
    user?: string;
    comment?: string;
  }>;
};

type FindingCardProps = {
  finding: Finding;
  onWorkflowAction?: (findingId: string, action: WorkflowAction, comment?: string) => Promise<void>;
  onAIQuery?: (query: string, context: AIContext) => Promise<string>;
};

export function FindingCard({ finding, onWorkflowAction, onAIQuery }: FindingCardProps) {
  const { t } = useTranslation();
  const [showAIPanel, setShowAIPanel] = useState(false);

  const handleWorkflowAction = async (action: WorkflowAction, comment?: string) => {
    if (onWorkflowAction) {
      await onWorkflowAction(finding.id, action, comment);
    }
  };

  const getSeverityColor = () => {
    switch (finding.severity) {
      case "critical":
        return "bg-[var(--accent-error)]/15 text-[var(--accent-error)]";
      case "high":
        return "bg-[var(--accent-2)]/15 text-[var(--accent-2)]";
      case "medium":
        return "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]";
      default:
        return "bg-[var(--ink-3)]/15 text-[var(--ink-3)]";
    }
  };

  return (
    <>
      <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2">
              <h4 className="text-sm font-semibold text-[var(--ink-1)]">{finding.title}</h4>
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${getSeverityColor()}`}>
                {t(`finding.severity.${finding.severity}`, { defaultValue: finding.severity })}
              </span>
            </div>
            <p className="mb-3 text-sm text-[var(--ink-2)]">{finding.description}</p>
            <div className="flex flex-wrap items-center gap-3">
              {finding.evidence && finding.evidence.length > 0 && (
                <EvidenceBadge evidence={finding.evidence} linkedTo={finding.id} />
              )}
              <button
                type="button"
                onClick={() => setShowAIPanel(true)}
                className="rounded-full border border-[var(--accent-1)] bg-[var(--accent-1)]/10 px-3 py-1 text-xs font-semibold text-[var(--accent-1)] transition hover:bg-[var(--accent-1)]/20"
              >
                {t("finding.askAI", { defaultValue: "Ask AI" })}
              </button>
            </div>
          </div>
        </div>
        {onWorkflowAction && (
          <div className="mt-4 border-t border-[var(--surface-3)] pt-4">
            <WorkflowActions
              currentStatus={finding.workflowStatus}
              onAction={handleWorkflowAction}
              workflowHistory={finding.workflowHistory}
            />
          </div>
        )}
      </div>

      {/* AI Panel Modal */}
      {showAIPanel && (
        <Modal
          open={showAIPanel}
          title={t("finding.aiInsights", { defaultValue: "AI Insights" })}
          onClose={() => setShowAIPanel(false)}
          size="lg"
        >
          <div className="h-[500px]">
            <AIPanel
              context={{
                engine: finding.engine,
                finding: finding.id,
              }}
              initialInsight={t("finding.aiInitialInsight", {
                defaultValue: `This finding from ${finding.engine} requires attention. Ask me anything about it.`,
              })}
              onQuery={onAIQuery}
              evidenceIds={finding.evidence?.map((e) => e.id) || []}
            />
          </div>
        </Modal>
      )}
    </>
  );
}


