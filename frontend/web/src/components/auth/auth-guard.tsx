"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-context";
import { useTranslation } from "react-i18next";

export function AuthGuard({
  children,
  role,
}: {
  children: React.ReactNode;
  role?: "admin" | "user";
}) {
  const { t } = useTranslation();
  const { token, role: currentRole } = useAuth();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Return a placeholder during SSR to prevent hydration mismatch
    return <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]" />;
  }

  if (!token) {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p>{t("auth.required")}</p>
        <Link href="/login" className="mt-3 inline-flex text-[var(--accent-1)] underline">
          {t("auth.signIn")}
        </Link>
      </div>
    );
  }

  if (role === "admin" && currentRole !== "admin") {
    return (
      <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 text-sm text-[var(--ink-2)]">
        <p>{t("auth.forbidden")}</p>
      </div>
    );
  }

  return <>{children}</>;
}
