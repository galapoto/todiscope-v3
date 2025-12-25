"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  languageFlags,
  applyDocumentLanguage,
  persistLanguage,
  supportedLanguages,
  type LanguageCode,
} from "@/lib/i18n";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const [open, setOpen] = useState(false);

  const current = (i18n.language || "fi") as LanguageCode;

  const handleSelect = (code: LanguageCode) => {
    i18n.changeLanguage(code);
    persistLanguage(code);
    applyDocumentLanguage(code);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-2 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-2)] shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t("language.label")}
      >
        <span className="text-base" aria-hidden="true">
          {languageFlags[current]}
        </span>
        {t(`language.${current}`)}
      </button>
      {open ? (
        <div className="absolute right-0 z-[9999] mt-2 w-44 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-2 shadow-[0_20px_40px_rgba(0,0,0,0.18)]">
          <ul role="listbox" className="flex flex-col gap-1">
            {supportedLanguages.map(({ code }) => (
              <li key={code}>
                <button
                  type="button"
                  onClick={() => handleSelect(code)}
                  className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.18em] transition ${
                    code === current
                      ? "bg-[var(--accent-1)]/15 text-[var(--accent-1)]"
                      : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
                  }`}
                  role="option"
                  aria-selected={code === current}
                >
                  <span className="text-base" aria-hidden="true">
                    {languageFlags[code]}
                  </span>
                  {t(`language.${code}`)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
