"use client";

import type { GateDecision } from "@/lib/permissions";
import { useTranslation } from "react-i18next";

export function Gated({
  decision,
  children,
}: {
  decision: GateDecision;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  if (decision.allowed) return <>{children}</>;
  return (
    <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4 text-sm text-[var(--ink-2)]">
      <p className="font-semibold">{t("states.error")}</p>
      <p className="mt-1 text-xs text-[var(--ink-3)]">{t(decision.messageKey)}</p>
    </div>
  );
}

