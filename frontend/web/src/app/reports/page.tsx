"use client";

import { AppShell } from "@/components/layout/app-shell";
import { ReportBuilder } from "@/components/reports/report-builder";
import { useTranslation } from "react-i18next";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function ReportsPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell title={t("reports.title")} subtitle={t("reports.subtitle")}>
        <ReportBuilder />
      </AppShell>
    </AuthGuard>
  );
}
