"use client";

import { ReactNode, useId } from "react";
import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

type WidgetShellProps = {
  title: string;
  subtitle?: string;
  pinned: boolean;
  onTogglePin: () => void;
  onRemove?: () => void;
  keyboardMode: "move" | "resize" | null;
  onToggleKeyboardMode: (mode: "move" | "resize") => void;
  onKeyboardAction: (mode: "move" | "resize", event: KeyboardEvent) => void;
  children: ReactNode;
};

export function WidgetShell({
  title,
  subtitle,
  pinned,
  onTogglePin,
  onRemove,
  keyboardMode,
  onToggleKeyboardMode,
  onKeyboardAction,
  children,
}: WidgetShellProps) {
  const { t } = useTranslation();
  const hintId = useId();
  return (
    <section className="flex h-full flex-col gap-4 overflow-hidden rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.08)]">
      <div className="widget-handle flex cursor-grab items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {subtitle ?? t("widgets.widget")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-[var(--ink-1)]">
            {title}
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onTogglePin}
            className={`widget-action rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] transition ${
              pinned
                ? "border-[var(--accent-2)] bg-[var(--accent-2)]/15 text-[var(--accent-2)]"
                : "border-[var(--surface-3)] bg-[var(--surface-2)] text-[var(--ink-3)] hover:border-[var(--accent-1)] hover:text-[var(--accent-1)]"
            }`}
          >
            {pinned ? t("widgets.pinned") : t("widgets.pin")}
          </button>
          <button
            type="button"
            onClick={() => onToggleKeyboardMode("move")}
            onKeyDown={(event) => onKeyboardAction("move", event)}
            aria-pressed={keyboardMode === "move"}
            aria-describedby={hintId}
            className={`widget-action rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] transition ${
              keyboardMode === "move"
                ? "border-[var(--accent-1)] bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                : "border-[var(--surface-3)] bg-[var(--surface-2)] text-[var(--ink-3)] hover:border-[var(--accent-1)] hover:text-[var(--accent-1)]"
            }`}
          >
            {t("widgets.keyboardMove")}
          </button>
          <button
            type="button"
            onClick={() => onToggleKeyboardMode("resize")}
            onKeyDown={(event) => onKeyboardAction("resize", event)}
            aria-pressed={keyboardMode === "resize"}
            aria-describedby={hintId}
            className={`widget-action rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] transition ${
              keyboardMode === "resize"
                ? "border-[var(--accent-1)] bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                : "border-[var(--surface-3)] bg-[var(--surface-2)] text-[var(--ink-3)] hover:border-[var(--accent-1)] hover:text-[var(--accent-1)]"
            }`}
          >
            {t("widgets.keyboardResize")}
          </button>
          {onRemove && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onRemove();
              }}
              className="widget-action rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)] transition hover:border-red-500 hover:bg-red-500/10 hover:text-red-500"
              aria-label={t("widgets.remove")}
            >
              ×
            </button>
          )}
        </div>
      </div>
      <p id={hintId} className="sr-only">
        {t("widgets.keyboardHint")}
      </p>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}
