"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export type WorkflowAction = "approve" | "reject" | "escalate" | "request_remediation" | "mark_resolved";

export type WorkflowStatus = "pending" | "approved" | "rejected" | "escalated" | "remediation_requested" | "resolved";

export interface WorkflowState {
  status: WorkflowStatus;
  history: Array<{
    action: WorkflowAction | string;
    timestamp: string;
    user?: string;
    comment?: string;
  }>;
}

type WorkflowActionsProps = {
  currentStatus: WorkflowStatus;
  onAction: (action: WorkflowAction, comment?: string) => Promise<void>;
  workflowHistory?: WorkflowState["history"];
  disabled?: boolean;
};

export function WorkflowActions({
  currentStatus,
  onAction,
  workflowHistory = [],
  disabled = false,
}: WorkflowActionsProps) {
  const { t } = useTranslation();
  const [actionModal, setActionModal] = useState<{
    action: WorkflowAction;
    open: boolean;
  } | null>(null);
  const [comment, setComment] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleActionClick = (action: WorkflowAction) => {
    setActionModal({ action, open: true });
    setComment("");
  };

  const handleConfirm = async () => {
    if (!actionModal) return;
    setIsProcessing(true);
    try {
      await onAction(actionModal.action, comment || undefined);
      setActionModal(null);
      setComment("");
    } catch (error) {
      console.error("Workflow action failed:", error);
      // Error handling is done by parent component
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusBadge = (status: WorkflowStatus) => {
    const statusConfig = {
      pending: {
        label: t("workflow.status.pending"),
        className: "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]",
      },
      approved: {
        label: t("workflow.status.approved"),
        className: "bg-[var(--accent-success)]/15 text-[var(--accent-success)]",
      },
      rejected: {
        label: t("workflow.status.rejected"),
        className: "bg-[var(--accent-error)]/15 text-[var(--accent-error)]",
      },
      escalated: {
        label: t("workflow.status.escalated"),
        className: "bg-[var(--accent-2)]/15 text-[var(--accent-2)]",
      },
      remediation_requested: {
        label: t("workflow.status.remediationRequested"),
        className: "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]",
      },
      resolved: {
        label: t("workflow.status.resolved"),
        className: "bg-[var(--accent-success)]/15 text-[var(--accent-success)]",
      },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${config.className}`}>
        {config.label}
      </span>
    );
  };

  const availableActions: WorkflowAction[] = [];
  if (currentStatus === "pending") {
    availableActions.push("approve", "reject", "escalate", "request_remediation");
  } else if (currentStatus === "remediation_requested") {
    availableActions.push("mark_resolved", "escalate");
  } else if (currentStatus === "escalated") {
    availableActions.push("approve", "reject");
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-[var(--ink-3)]">{t("workflow.status.label")}:</span>
          {getStatusBadge(currentStatus)}
        </div>
        {workflowHistory.length > 0 && (
          <button
            type="button"
            onClick={() => setActionModal({ action: "approve", open: true })}
            className="text-xs text-[var(--ink-3)] hover:text-[var(--accent-1)]"
          >
            {t("workflow.viewHistory")} ({workflowHistory.length})
          </button>
        )}
        {availableActions.length > 0 && !disabled && (
          <div className="flex flex-wrap gap-2">
            {availableActions.includes("approve") && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleActionClick("approve")}
                disabled={isProcessing}
              >
                {t("workflow.actions.approve")}
              </Button>
            )}
            {availableActions.includes("reject") && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleActionClick("reject")}
                disabled={isProcessing}
              >
                {t("workflow.actions.reject")}
              </Button>
            )}
            {availableActions.includes("escalate") && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleActionClick("escalate")}
                disabled={isProcessing}
              >
                {t("workflow.actions.escalate")}
              </Button>
            )}
            {availableActions.includes("request_remediation") && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleActionClick("request_remediation")}
                disabled={isProcessing}
              >
                {t("workflow.actions.requestRemediation")}
              </Button>
            )}
            {availableActions.includes("mark_resolved") && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleActionClick("mark_resolved")}
                disabled={isProcessing}
              >
                {t("workflow.actions.markResolved")}
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {actionModal && (
        <Modal
          open={actionModal.open}
          title={t(`workflow.actions.${actionModal.action}`)}
          onClose={() => {
            setActionModal(null);
            setComment("");
          }}
          size="md"
        >
          <div className="space-y-4">
            <p className="text-sm text-[var(--ink-2)]">
              {t(`workflow.confirm.${actionModal.action}`)}
            </p>
            <div>
              <label className="mb-2 block text-sm font-medium text-[var(--ink-2)]">
                {t("workflow.comment")} ({t("workflow.commentOptional")})
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full rounded-lg border border-[var(--surface-3)] bg-[var(--surface-1)] p-3 text-sm text-[var(--ink-1)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                rows={4}
                placeholder={t("workflow.commentPlaceholder")}
              />
            </div>
            {workflowHistory.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-[var(--ink-1)]">
                  {t("workflow.history")}
                </h4>
                <div className="max-h-40 space-y-2 overflow-y-auto rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-3">
                  {workflowHistory.map((entry, idx) => (
                    <div key={idx} className="text-xs text-[var(--ink-2)]">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {t(`workflow.actions.${entry.action}`)}
                        </span>
                        <span className="text-[var(--ink-3)]">
                          {new Date(entry.timestamp).toLocaleString()}
                        </span>
                      </div>
                      {entry.comment && (
                        <p className="mt-1 text-[var(--ink-3)]">{entry.comment}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => {
                  setActionModal(null);
                  setComment("");
                }}
                disabled={isProcessing}
              >
                {t("workflow.cancel")}
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirm}
                disabled={isProcessing}
              >
                {isProcessing ? t("workflow.processing") : t("workflow.confirm")}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

