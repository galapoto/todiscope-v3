"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useTranslation } from "react-i18next";
import { EngineCoverageMatrix } from "@/components/admin/engine-coverage-matrix";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function CoveragePage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("coverage.title", { defaultValue: "Engine Coverage Matrix" })}
        subtitle={t("coverage.subtitle", { defaultValue: "Internal validation dashboard" })}
      >
        <EngineCoverageMatrix />
      </AppShell>
    </AuthGuard>
  );
}

