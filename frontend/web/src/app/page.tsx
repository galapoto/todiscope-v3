"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { useEngines } from "@/hooks/use-engines";
import { useDatasetVersions } from "@/hooks/use-dataset-versions";
import { useEngineResults } from "@/components/engines/engine-results-context";
import { useTranslation } from "react-i18next";

export default function Home() {
  const { t } = useTranslation();
  const datasets = useDatasetVersions().data ?? [];
  const engines = useEngines().data ?? [];
  const results = useEngineResults().results;

  const heroStats = useMemo(() => {
    const datasetList = datasets ?? [];
    const activeRuns = results.filter((result) => result.kind === "run").length;
    const totalReports = results.filter((result) => result.kind === "report").length;
    const latest = datasetList[0];
    return [
      {
        label: t("home.stats.datasets", { defaultValue: "Dataset versions" }),
        value: datasetList.length,
        detail: latest
          ? t("home.stats.latestDataset", {
              defaultValue: "Latest: {{date}}",
              date: new Date(latest.created_at).toLocaleDateString(),
            })
          : t("home.stats.noDataset", { defaultValue: "No datasets yet" }),
      },
      {
        label: t("home.stats.engines", { defaultValue: "Engines in registry" }),
        value: engines.length,
        detail: t("home.stats.engineCoverage", { defaultValue: "Surface coverage only (enable engines in backend to run)" }),
      },
      {
        label: t("home.stats.runs", { defaultValue: "Recent runs" }),
        value: activeRuns,
        detail: t("home.stats.recentActivity", { defaultValue: "Tracked in this browser session" }),
      },
      {
        label: t("home.stats.reports", { defaultValue: "Reports captured" }),
        value: totalReports,
        detail: t("home.stats.insightReady", { defaultValue: "Exports available after generation" }),
      },
    ];
  }, [datasets, engines.length, results, t]);

  return (
    <AuthGuard>
      <AppShell
        title={t("home.title", { defaultValue: "Control Deck" })}
        subtitle={t("home.subtitle", { defaultValue: "Operational readiness, supplier oversight, and audit visibility" })}
      >
        <div className="space-y-8">
          <section className="rounded-3xl border border-[var(--surface-3)] bg-gradient-to-br from-[rgba(37,99,235,0.2)] to-[rgba(15,23,42,0.6)] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.25)] text-white">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.4em] text-white/60">
                  {t("home.hero.tagline", {
                    defaultValue: "Responsive governance inspired by v2 command decks",
                  })}
                </p>
                <h1 className="text-4xl font-semibold leading-tight">
                  {t("home.hero.title", {
                    defaultValue: "Operational visibility for every engine, supplier, and dataset",
                  })}
                </h1>
                <p className="max-w-2xl text-sm text-white/80">
                  {t("home.hero.body", {
                    defaultValue:
                      "Track suppliers, enforce dataset-version law, and keep proof of life on every analytical engine without guesswork. Designed as a generational upgrade from the v2 control room.",
                  })}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  href="/dashboard"
                  className="btn btn-primary text-sm font-semibold"
                >
                  {t("home.hero.cta1", { defaultValue: "Open Command Pane" })}
                </Link>
                <Link
                  href="/reports"
                  className="btn btn-ghost text-sm font-semibold"
                >
                  {t("home.hero.cta2", { defaultValue: "Build a report" })}
                </Link>
              </div>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {heroStats.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-white/20 bg-white/5 px-4 py-5 backdrop-blur"
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-white/70">{stat.label}</p>
                  <p className="mt-2 text-3xl font-bold">{stat.value}</p>
                  <p className="text-xs text-white/70">{stat.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[var(--ink-1)]">
                  {t("home.suppliers.title", { defaultValue: "Suppliers & partners" })}
                </h2>
                <p className="text-sm text-[var(--ink-3)]">
                  {t("home.suppliers.subtitle", {
                    defaultValue:
                      "Supplier oversight becomes available once supplier datasets are imported and normalized. No mock supplier data is shown.",
                  })}
                </p>
              </div>
              <Link
                href="/docs/ENGINE_INDEX.md"
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary btn-sm"
                >
                  {t("home.suppliers.docs", { defaultValue: "View plans" })}
                </Link>
            </div>
            <div className="mt-6 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
              <p>
                {t("home.suppliers.empty", {
                  defaultValue:
                    "No supplier visibility yet. Import a supplier dataset to populate supplier oversight.",
                })}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href="/workflow/import" className="btn btn-primary btn-sm">
                  {t("home.suppliers.cta", { defaultValue: "Import dataset" })}
                </Link>
                <Link href="/dashboard" className="btn btn-secondary btn-sm">
                  {t("home.suppliers.cta2", { defaultValue: "Open dashboard" })}
                </Link>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-[var(--ink-1)]">
                {t("home.signals.title", { defaultValue: "Operational signals" })}
              </h2>
              <p className="text-xs text-[var(--ink-3)]">
                {t("home.signals.subtitle", {
                  defaultValue: "Signals render from available state only (no synthetic realtime).",
                })}
              </p>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[
                {
                  label: t("home.signals.datasets", { defaultValue: "Datasets" }),
                  value: datasets.length,
                  detail: datasets.length ? t("home.signals.datasetsOk", { defaultValue: "Ready for engine runs." }) : t("home.signals.datasetsNone", { defaultValue: "Import required." }),
                },
                {
                  label: t("home.signals.registry", { defaultValue: "Engine registry" }),
                  value: engines.length,
                  detail: t("home.signals.registryHint", { defaultValue: "Enable engines in backend to execute." }),
                },
                {
                  label: t("home.signals.activity", { defaultValue: "Local activity" }),
                  value: results.length,
                  detail: t("home.signals.activityHint", { defaultValue: "Runs/reports recorded by this session." }),
                },
              ].map((stat, index) => (
                <div
                  key={stat.label}
                  className={`rounded-2xl border p-4 ${
                    index % 2 === 0
                      ? "border-green-500/30 bg-green-500/10"
                      : "border-blue-500/30 bg-blue-500/10"
                  }`}
                >
                  <p className="text-xs uppercase tracking-[0.3em] text-[var(--ink-3)]">
                    {stat.label}
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-[var(--ink-1)]">{stat.value}</p>
                  <p className="text-xs text-[var(--ink-3)]">{stat.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6 shadow-lg">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[var(--ink-1)]">
                  {t("home.timeline.title", { defaultValue: "Journey to audit-readiness" })}
                </h2>
                <p className="text-sm text-[var(--ink-3)]">
                  {t("home.timeline.subtitle", {
                    defaultValue:
                      "Track steps from data ingestion through AI augmented reports, just like the v2 control room.",
                  })}
                </p>
              </div>
              <div className="flex gap-2">
                <Link
                  href="/workflow/import"
                  className="btn btn-ghost btn-sm text-[var(--ink-1)] hover:bg-[var(--surface-3)]"
                >
                  {t("home.timeline.import", { defaultValue: "Ingest data" })}
                </Link>
                <Link
                  href="/workflow/report"
                  className="btn btn-ghost btn-sm text-[var(--ink-1)] hover:bg-[var(--surface-3)]"
                >
                  {t("home.timeline.report", { defaultValue: "Generate report" })}
                </Link>
              </div>
            </div>
            <div className="mt-6 space-y-3">
              {[
                {
                  label: t("home.timeline.stage1", { defaultValue: "Import" }),
                  detail: t("home.timeline.stage1Detail", {
                    defaultValue: "DatasetVersion creation anchors evidence and metadata for every downstream action.",
                  }),
                },
                {
                  label: t("home.timeline.stage2", { defaultValue: "Normalize" }),
                  detail: t("home.timeline.stage2Detail", {
                    defaultValue: "Transformations and assumptions are recorded to keep engines accountable.",
                  }),
                },
                {
                  label: t("home.timeline.stage3", { defaultValue: "Calculate & Report" }),
                  detail: t("home.timeline.stage3Detail", {
                    defaultValue: "Every engine run and AI narrative references a DatasetVersion and downstream evidence.",
                  }),
                },
              ].map((stage, index) => (
                <div
                  key={stage.label}
                  className={`rounded-2xl border p-4 ${
                    index % 2 === 0
                      ? "border-green-500/30 bg-green-500/10"
                      : "border-blue-500/30 bg-blue-500/10"
                  }`}
                >
                  <p className="text-xs uppercase tracking-[0.3em] text-[var(--ink-3)]">
                    {stage.label}
                  </p>
                  <p className="text-sm text-[var(--ink-1)]">{stage.detail}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
