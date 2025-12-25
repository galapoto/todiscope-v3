"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";
import { TodiScopeLogo } from "@/components/brand/todiscope-logo";
import { engineRegistry, getEngineDefinition } from "@/engines/registry";
import { TeamMembers } from "@/components/layout/team-members";
import { useAuth } from "@/components/auth/auth-context";
import { useEngines } from "@/hooks/use-engines";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  LayoutDashboard,
  FileText,
  Settings,
  Grid3X3,
  TrendingUp,
  Building2,
  Database,
  Scale,
  Shield,
  Gavel,
  AlertTriangle,
  FileCheck,
  Briefcase,
  DollarSign,
  Home,
} from "lucide-react";

type SidebarProps = {
  isOpen: boolean;
  onToggle: () => void;
};

// Engine icons mapping - using appropriate icons for each engine
const getEngineIcon = (engineId: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    engine_csrd: <FileText className="h-5 w-5" />,
    engine_financial_forensics: <TrendingUp className="h-5 w-5" />,
    engine_construction_cost_intelligence: <Building2 className="h-5 w-5" />,
    engine_audit_readiness: <Shield className="h-5 w-5" />,
    engine_enterprise_capital_debt_readiness: <Scale className="h-5 w-5" />,
    engine_data_migration_readiness: <Database className="h-5 w-5" />,
    engine_erp_integration_readiness: <Database className="h-5 w-5" />,
    engine_enterprise_deal_transaction_readiness: <Briefcase className="h-5 w-5" />,
    engine_enterprise_litigation_dispute: <Gavel className="h-5 w-5" />,
    engine_regulatory_readiness: <FileCheck className="h-5 w-5" />,
    engine_enterprise_insurance_claim_forensics: <AlertTriangle className="h-5 w-5" />,
    engine_distressed_asset_debt_stress: <DollarSign className="h-5 w-5" />,
  };
  return iconMap[engineId] || <LayoutDashboard className="h-5 w-5" />;
};

export function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const { t } = useTranslation();
  const pathname = usePathname();
  const { role } = useAuth();
  const enginesQuery = useEngines();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["engines"]));
  const [searchQuery, setSearchQuery] = useState("");

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const engines = (enginesQuery.data ?? Object.keys(engineRegistry)).map((engineId) =>
    getEngineDefinition(engineId)
  );
  const filteredEngines = engines.filter((engine) =>
    engine.display_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-50 flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--surface-3)] bg-[var(--surface-1)] text-[var(--ink-2)] shadow-lg transition-all duration-200 hover:bg-[var(--surface-2)] hover:scale-105"
        aria-label="Open sidebar"
      >
        <ChevronRight className="h-5 w-5" />
      </button>
    );
  }

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[280px] border-r border-[var(--surface-3)] bg-[var(--surface-1)] shadow-xl transition-transform duration-300 ease-in-out">
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-[var(--surface-3)] px-4">
        <Link
          href="/"
          className="flex items-center gap-2 transition hover:text-[var(--accent-1)]"
        >
          <div className="flex h-[72px] w-[72px] items-center justify-center rounded-lg bg-blue-600/10 dark:bg-blue-400/10">
            <TodiScopeLogo size={45} showWordmark={false} />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-[var(--ink-1)]">TodiScope</span>
            <span className="text-xs text-[var(--ink-3)]">AI Governance</span>
          </div>
        </Link>
        <button
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--ink-3)] transition-all duration-200 hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] hover:scale-110"
          aria-label="Close sidebar"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      </div>

      {/* Current User - Below Logo */}
      <div className="border-b border-[var(--surface-3)] p-4">
        <TeamMembers showCurrentUserOnly />
      </div>

      {/* Search */}
      <div className="border-b border-[var(--surface-3)] p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ink-3)]" />
          <input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] px-10 py-2 text-sm text-[var(--ink-1)] placeholder:text-[var(--ink-3)] focus:border-[var(--accent-1)] focus:outline-none"
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto pb-4">
        {/* Engines Section */}
        <div>
          <button
            onClick={() => toggleSection("engines")}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-[var(--ink-2)] transition hover:bg-[var(--surface-2)]"
          >
            <div className="flex items-center gap-3">
              <LayoutDashboard className="h-5 w-5" />
              <span>Engines</span>
            </div>
            <ChevronRight
              className={`h-4 w-4 transition-transform ${expandedSections.has("engines") ? "rotate-90" : ""}`}
            />
          </button>
          {expandedSections.has("engines") && (
            <div className="space-y-1 px-4 pb-2">
              {filteredEngines.map((engine) => {
                const isActive = pathname.includes(`/engines/${engine.engine_id}`) || 
                                (pathname === "/dashboard" && engine.engine_id === "engine_financial_forensics");
                return (
                  <Link
                    key={engine.engine_id}
                    href={`/engines/${engine.engine_id}`}
                    className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                      isActive
                        ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                        : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
                    }`}
                  >
                    <span className={`${isActive ? "text-[var(--accent-1)]" : "text-[var(--ink-3)] group-hover:text-[var(--accent-1)]"}`}>
                      {getEngineIcon(engine.engine_id)}
                    </span>
                    <span className="flex-1 truncate">{engine.display_name}</span>
                    {isActive && (
                      <div className="h-2 w-2 rounded-full bg-[var(--accent-1)]" />
                    )}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Main Navigation */}
        <div className="mt-2 space-y-1 px-4">
          <Link
            href="/"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              pathname === "/"
                ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
            }`}
          >
            <Home className="h-5 w-5" />
            <span suppressHydrationWarning>{t("app.navigation.home", { defaultValue: "Home" })}</span>
          </Link>
          <Link
            href="/dashboard"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              pathname === "/dashboard"
                ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
            }`}
          >
            <LayoutDashboard className="h-5 w-5" />
            <span>{t("app.navigation.dashboard")}</span>
          </Link>
          <Link
            href="/ocr"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              pathname === "/ocr"
                ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
            }`}
          >
            <FileText className="h-5 w-5" />
            <span>{t("app.navigation.ocr", { defaultValue: "OCR" })}</span>
          </Link>
          <Link
            href="/audit"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              pathname === "/audit" || pathname?.startsWith("/audit")
                ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
            }`}
          >
            <Shield className="h-5 w-5" />
            <span>{t("app.navigation.audit", { defaultValue: "Audit" })}</span>
          </Link>
          <Link
            href="/settings"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              pathname === "/settings"
                ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
            }`}
          >
            <Settings className="h-5 w-5" />
            <span>{t("app.navigation.settings")}</span>
          </Link>
          {role === "admin" ? (
            <Link
              href="/coverage"
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                pathname === "/coverage"
                  ? "bg-[var(--accent-1)]/10 text-[var(--accent-1)]"
                  : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
              }`}
            >
              <Grid3X3 className="h-5 w-5" />
              <span>{t("app.navigation.coverage")}</span>
            </Link>
          ) : null}
        </div>

        {/* Team Members Section */}
        <div className="mt-6 px-4">
          <TeamMembers />
        </div>
      </div>
    </aside>
  );
}
