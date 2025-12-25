"use client";

import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

type ModalProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  size?: "sm" | "md" | "lg" | "full";
  modal?: boolean;
  children: React.ReactNode;
};

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-xl",
  lg: "max-w-3xl",
  full: "max-w-[90vw] h-[85vh]",
} as const;

export function Modal({
  open,
  title,
  onClose,
  size = "md",
  modal = true,
  children,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const { t } = useTranslation();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      if (modal) {
        dialog.showModal();
      } else {
        dialog.show();
      }
      closeRef.current?.focus();
    }
    if (!open && dialog.open) {
      dialog.close();
    }
  }, [open, modal]);

  return (
    <dialog
      ref={ref}
      className={`dialog-backdrop dialog-enter w-full ${sizeClasses[size]} rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-[var(--ink-1)] shadow-[0_24px_80px_rgba(0,0,0,0.25)]`}
      onClose={onClose}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <button
          type="button"
          onClick={onClose}
          className="btn btn-ghost"
          aria-label={t("modal.close")}
          ref={closeRef}
        >
          {t("modal.close")}
        </button>
      </div>
      <div className="mt-4 max-h-[70vh] overflow-y-auto pr-1">{children}</div>
    </dialog>
  );
}
