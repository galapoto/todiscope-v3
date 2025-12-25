"use client";

import { useTheme } from "@/components/theme/theme-context";
import { useTranslation } from "react-i18next";

export function ThemeToggle() {
  const { mode, toggle } = useTheme();
  const { t } = useTranslation();
  const nextLabel = mode === "dark" ? t("theme.day") : t("theme.night");

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={nextLabel}
      className="inline-flex items-center gap-2 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-2)] shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <span className="h-2 w-2 rounded-full bg-[var(--accent-1)] shadow-[0_0_0_4px_var(--ring)]" />
      {mode === "dark" ? t("theme.night") : t("theme.day")}
    </button>
  );
}
