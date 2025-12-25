"use client";

import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useTranslation } from "react-i18next";

export function DegradedBanner() {
  const { t } = useTranslation();
  const pathname = usePathname();
  
  // Hide banner on authentication pages (login, register)
  const isAuthPage = pathname?.startsWith("/login") || pathname?.startsWith("/register");

  const { data, isError, isLoading } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => api.getBackendHealth(),
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: 1,
    enabled: !isAuthPage,
  });

  if (isAuthPage) return null;

  // Don't show anything while loading
  if (isLoading) return null;

  // Only show error if backend is actually unavailable (network error)
  // This means the request failed completely, not just that status is degraded
  if (isError) {
    return (
      <div className="border-b border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 px-4 py-2 text-xs text-[var(--accent-error)]">
        {t("system.backendUnavailable", { defaultValue: "Backend unavailable. Some data may be stale." })}
      </div>
    );
  }

  // If we have data, check if it's degraded
  if (data && data.status === "degraded") {
    return (
      <div className="border-b border-[var(--accent-warn)]/40 bg-[var(--accent-warn)]/10 px-4 py-2 text-xs text-[var(--accent-warn)]">
        {t("system.degraded", { defaultValue: "System degraded. Partial data may be shown." })}
      </div>
    );
  }

  // Backend is OK
  return null;

  return (
    <div className="border-b border-[var(--accent-warn)]/40 bg-[var(--accent-warn)]/10 px-4 py-2 text-xs text-[var(--accent-warn)]">
      {t("system.degraded", { defaultValue: "System degraded. Partial data may be shown." })}
    </div>
  );
}
