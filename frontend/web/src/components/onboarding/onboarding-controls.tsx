"use client";

import { Button } from "@/components/ui/button";
import { useOnboarding } from "@/components/onboarding/onboarding-context";
import { useTranslation } from "react-i18next";

export function OnboardingControls() {
  const { t } = useTranslation();
  const { active, completed, resume, start } = useOnboarding();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        if (active) return;
        if (completed) {
          start();
        } else {
          resume();
        }
      }}
    >
      {t("onboarding.actions.help")}
    </Button>
  );
}
