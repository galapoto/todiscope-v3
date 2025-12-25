"use client";

import { TodiScopeLogo } from "@/components/brand/todiscope-logo";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function AuthScreen({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="theme-transition min-h-screen bg-[radial-gradient(900px_circle_at_20%_-10%,rgba(255,228,179,0.7)_0%,transparent_70%),radial-gradient(800px_circle_at_90%_10%,rgba(94,234,212,0.3)_0%,transparent_65%),linear-gradient(160deg,rgba(255,255,255,0.7)_0%,rgba(255,240,214,0.2)_45%,rgba(13,19,18,0.12)_100%)] dark:bg-[radial-gradient(900px_circle_at_20%_-10%,rgba(15,118,110,0.18)_0%,transparent_70%),radial-gradient(800px_circle_at_90%_10%,rgba(251,146,60,0.18)_0%,transparent_65%),linear-gradient(160deg,rgba(9,13,13,0.9)_0%,rgba(15,19,18,0.96)_45%,rgba(9,12,12,0.95)_100%)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <TodiScopeLogo size={40} showWordmark className="text-[var(--ink-1)]" />
          <div className="hidden sm:block">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--ink-3)]">
              {subtitle}
            </p>
            <h1 className="mt-1 text-lg font-semibold text-[var(--ink-1)]">{title}</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl justify-center px-6 pb-12 pt-2">
        <div className="w-full max-w-md rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)]/85 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.18)] backdrop-blur">
          {children}
        </div>
      </main>
    </div>
  );
}

