"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useTranslation } from "react-i18next";
import { AuthGuard } from "@/components/auth/auth-guard";
import dynamic from "next/dynamic";
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { resolveEngineRouteId } from "@/lib/engine-id-mapping";

function DashboardLoading() {
  const { t } = useTranslation();
  return (
    <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
      {t("states.loading", { defaultValue: "Loading..." })}
    </div>
  );
}

const DashboardGrid = dynamic(
  () => import("@/components/dashboard/dashboard-grid").then((mod) => mod.DashboardGrid),
  {
    ssr: false,
    loading: () => <DashboardLoading />,
  }
);

function DashboardEngineRedirect() {
  const router = useRouter();
  const params = useSearchParams();
  const engine = params.get("engine");

  useEffect(() => {
    if (!engine) return;
    const routeId = resolveEngineRouteId(engine);
    if (!routeId) {
      console.error(`Unknown engine slug "${engine}" in dashboard redirect.`);
      return;
    }
    router.replace(`/engines/${routeId}`);
  }, [engine, router]);

  return null;
}

export default function DashboardPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell title={t("dashboard.title")} subtitle={t("dashboard.subtitle")}>
        <Suspense fallback={null}>
          <DashboardEngineRedirect />
        </Suspense>
        <DashboardGrid />
      </AppShell>
    </AuthGuard>
  );
}
