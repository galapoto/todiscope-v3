"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-context";
import { useTranslation } from "react-i18next";

export function AuthStatus() {
  const { t } = useTranslation();
  const { token, email, logout } = useAuth();

  if (!token) {
    return (
      <Link href="/login" className="btn btn-ghost btn-sm">
        {t("auth.signIn")}
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-[var(--ink-3)]">
      <span className="hidden sm:inline">{email ?? t("auth.signedIn")}</span>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void logout()}>
        {t("auth.signOut")}
      </button>
    </div>
  );
}
