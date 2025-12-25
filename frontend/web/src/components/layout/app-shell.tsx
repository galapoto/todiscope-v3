"use client";

import { useState } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { DatasetSelector } from "@/components/data/dataset-selector";
import { SearchInput } from "@/components/search/search-input";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { OnboardingControls } from "@/components/onboarding/onboarding-controls";
import { AuthStatus } from "@/components/auth/auth-status";
import { Sidebar } from "@/components/layout/sidebar";
import { TodiScopeLogo } from "@/components/brand/todiscope-logo";
import { useTranslation } from "react-i18next";

export function AppShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="theme-transition min-h-screen bg-[radial-gradient(900px_circle_at_20%_-10%,rgba(255,228,179,0.7)_0%,transparent_70%),radial-gradient(800px_circle_at_90%_10%,rgba(94,234,212,0.3)_0%,transparent_65%),linear-gradient(160deg,rgba(255,255,255,0.7)_0%,rgba(255,240,214,0.2)_45%,rgba(13,19,18,0.12)_100%)] dark:bg-[radial-gradient(900px_circle_at_20%_-10%,rgba(15,118,110,0.18)_0%,transparent_70%),radial-gradient(800px_circle_at_90%_10%,rgba(251,146,60,0.18)_0%,transparent_65%),linear-gradient(160deg,rgba(9,13,13,0.9)_0%,rgba(15,19,18,0.96)_45%,rgba(9,12,12,0.95)_100%)]">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <main
        className={`transition-all duration-300 ease-in-out ${
          sidebarOpen ? "ml-[280px]" : "ml-0"
        } flex min-w-0 flex-col gap-6 px-4 py-6`}
      >
        <header className="flex flex-col gap-4 rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)]/85 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.08)] backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                aria-label={t("app.navigation.dashboard", { defaultValue: "Dashboard" })}
                className="flex h-[72px] w-[72px] items-center justify-center rounded-lg bg-blue-600/10 transition hover:bg-blue-600/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-1)] dark:bg-blue-400/10 dark:hover:bg-blue-400/20"
              >
                <TodiScopeLogo size={48} showWordmark={false} />
              </Link>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--ink-3)]">
                  {subtitle}
                </p>
                <h2 className="mt-2 text-3xl font-semibold text-[var(--ink-1)]">
                  {typeof title === "string" ? title : title}
                </h2>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <SearchInput />
              <DatasetSelector />
              <OnboardingControls />
              <AuthStatus />
              <LanguageSwitcher />
              <ThemeToggle />
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-[var(--ink-3)]">
            <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
              {t("app.liveData")}
            </span>
            <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
              {t("app.aiLayer")}
            </span>
            <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1">
              {t("app.secureDefault")}
            </span>
          </div>
        </header>
        <section className="animate-rise">{children}</section>
      </main>
      <OnboardingTour />
    </div>
  );
}
