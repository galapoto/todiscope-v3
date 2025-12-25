"use client";

import { useMemo } from "react";
import { useTranslation } from "react-i18next";

export type Strength = {
  score: number;
  checks: {
    length: boolean;
    upper: boolean;
    number: boolean;
    symbol: boolean;
  };
};

export function usePasswordStrength(password: string): Strength {
  return useMemo(() => {
    const checks = {
      length: password.length >= 12,
      upper: /[A-Z]/.test(password),
      number: /[0-9]/.test(password),
      symbol: /[^A-Za-z0-9]/.test(password),
    };
    const score = Object.values(checks).filter(Boolean).length;
    return { score, checks };
  }, [password]);
}

export function PasswordStrength({ password }: { password: string }) {
  const { t } = useTranslation();
  const { score, checks } = usePasswordStrength(password);

  return (
    <div className="space-y-2 text-xs text-[var(--ink-3)]">
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-2)]">
          <div
            className="h-full bg-[var(--accent-1)] transition-all"
            style={{ width: `${(score / 4) * 100}%` }}
          />
        </div>
        <span className="text-[var(--ink-2)]">
          {t(`auth.strength.${score}`)}
        </span>
      </div>
      <ul className="list-disc pl-4">
        <li className={checks.length ? "text-[var(--accent-1)]" : ""}>
          {t("auth.requirements.length")}
        </li>
        <li className={checks.upper ? "text-[var(--accent-1)]" : ""}>
          {t("auth.requirements.upper")}
        </li>
        <li className={checks.number ? "text-[var(--accent-1)]" : ""}>
          {t("auth.requirements.number")}
        </li>
        <li className={checks.symbol ? "text-[var(--accent-1)]" : ""}>
          {t("auth.requirements.symbol")}
        </li>
      </ul>
    </div>
  );
}
