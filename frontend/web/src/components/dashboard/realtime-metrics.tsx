"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api-client";

export function RealtimeMetrics() {
  const { t } = useTranslation();
  const health = useQuery({
    queryKey: ["backend-health"],
    queryFn: () => api.getBackendHealth(),
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: false,
  });

  if (health.isLoading) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-3)]">
        {t("states.loading", { defaultValue: "Loading..." })}
      </div>
    );
  }

  if (health.isError || !health.data) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p className="font-semibold text-[var(--ink-1)]">
          {t("system.backendUnavailable", {
            defaultValue: "Backend is unavailable. No live system metrics can be shown.",
          })}
        </p>
      </div>
    );
  }

  const entries = Object.entries(health.data.checks || {});
  const statusLabel =
    health.data.status === "ok"
      ? t("states.success", { defaultValue: "Healthy" })
      : t("system.degraded", { defaultValue: "Degraded" });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`w-fit rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
            health.data.status === "ok"
              ? "bg-[var(--accent-success)]/15 text-[var(--accent-success)]"
              : "bg-[var(--accent-warning)]/15 text-[var(--accent-warning)]"
          }`}
        >
          {statusLabel}
        </span>
        <span className="text-xs text-[var(--ink-3)]">
          {t("system.healthChecks", { defaultValue: "Health checks" })}: {entries.length}
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {entries.slice(0, 4).map(([key, check]) => (
          <div
            key={key}
            className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {key}
            </p>
            <div className="mt-2 flex items-baseline justify-between gap-2">
              <span className="text-lg font-semibold text-[var(--ink-1)]">
                {String(check.status)}
              </span>
              {typeof check.latency_ms === "number" ? (
                <span className="text-xs text-[var(--ink-3)]">{check.latency_ms}ms</span>
              ) : null}
            </div>
            {check.detail ? (
              <p className="mt-2 text-xs text-[var(--ink-3)]">{check.detail}</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
