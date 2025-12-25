"use client";

import { useEffect, useMemo, useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { useOnboarding } from "@/components/onboarding/onboarding-context";
import { useTranslation } from "react-i18next";

type TourStep = {
  id: string;
  titleKey: string;
  bodyKey: string;
  target: string;
};

function findTarget(selector: string) {
  if (typeof document === "undefined") return null;
  return document.querySelector<HTMLElement>(selector);
}

export function OnboardingTour() {
  const { t } = useTranslation();
  const { active, step, completed, seen, start, skip, next, back, close } = useOnboarding();
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);

  const steps = useMemo<TourStep[]>(
    () => [
      {
        id: "nav-dashboard",
        titleKey: "onboarding.steps.dashboard.title",
        bodyKey: "onboarding.steps.dashboard.body",
        target: "[data-onboard='nav-dashboard']",
      },
      {
        id: "nav-reports",
        titleKey: "onboarding.steps.reports.title",
        bodyKey: "onboarding.steps.reports.body",
        target: "[data-onboard='nav-reports']",
      },
      {
        id: "dataset-selector",
        titleKey: "onboarding.steps.datasets.title",
        bodyKey: "onboarding.steps.datasets.body",
        target: "[data-onboard='dataset-selector']",
      },
      {
        id: "search",
        titleKey: "onboarding.steps.search.title",
        bodyKey: "onboarding.steps.search.body",
        target: "[data-onboard='global-search']",
      },
      {
        id: "report-action",
        titleKey: "onboarding.steps.report.title",
        bodyKey: "onboarding.steps.report.body",
        target: "[data-onboard='report-generate']",
      },
    ],
    []
  );

  useEffect(() => {
    if (!seen && !active) {
      setWelcomeOpen(true);
    }
  }, [seen, active]);

  useEffect(() => {
    if (!active) return;
    const current = steps[step];
    if (!current) return;
    const target = findTarget(current.target);
    if (!target) {
      setAnchorRect(null);
      return;
    }
    target.setAttribute("data-onboard-active", "true");
    const updateRect = () => {
      setAnchorRect(target.getBoundingClientRect());
    };
    updateRect();
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      target.removeAttribute("data-onboard-active");
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [active, step, steps]);

  const current = steps[step];
  const isLast = step >= steps.length - 1;
  const tooltipStyle = anchorRect
    ? {
        top: Math.max(24, anchorRect.bottom + 12),
        left: Math.max(24, anchorRect.left),
      }
    : { top: 120, left: 24 };

  return (
    <>
      <Modal
        open={welcomeOpen}
        onClose={() => {
          setWelcomeOpen(false);
          close();
        }}
        title={t("onboarding.welcome.title")}
        size="md"
        modal={false}
      >
        <div className="space-y-4 text-sm text-[var(--ink-2)]">
          <p>{t("onboarding.welcome.body")}</p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={() => {
                setWelcomeOpen(false);
                start();
              }}
            >
              {t("onboarding.actions.start")}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setWelcomeOpen(false);
                close();
              }}
            >
              {t("onboarding.actions.later")}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setWelcomeOpen(false);
                skip();
              }}
            >
              {t("onboarding.actions.skip")}
            </Button>
          </div>
        </div>
      </Modal>
      {active && current ? (
        <div className="fixed inset-0 z-50 pointer-events-none">
          <div className="absolute inset-0 bg-black/25" />
          <div
            className="absolute z-50 max-w-xs rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4 text-sm text-[var(--ink-2)] shadow-[0_20px_60px_rgba(0,0,0,0.25)] pointer-events-auto"
            style={tooltipStyle}
            role="dialog"
            aria-live="polite"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t(current.titleKey)}
            </p>
            <p className="mt-2">{t(current.bodyKey)}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Button variant="secondary" size="sm" onClick={back} disabled={step === 0}>
                {t("onboarding.actions.back")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  if (isLast) {
                    skip();
                  } else {
                    next();
                  }
                }}
              >
                {isLast ? t("onboarding.actions.finish") : t("onboarding.actions.next")}
              </Button>
              <Button variant="ghost" size="sm" onClick={skip}>
                {t("onboarding.actions.skip")}
              </Button>
              <Button variant="ghost" size="sm" onClick={close}>
                {t("modal.close")}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
