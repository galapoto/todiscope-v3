"use client";

import { useSearch } from "@/components/search/search-context";
import { useTranslation } from "react-i18next";

export function SearchInput() {
  const { t } = useTranslation();
  const { query, setQuery, clear } = useSearch();

  return (
    <div className="relative w-full max-w-xs">
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={t("search.placeholder")}
        aria-label={t("search.placeholder")}
        data-onboard="global-search"
        className="w-full rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 pr-10 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
      />
      {query ? (
        <button
          type="button"
          onClick={clear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-3)] hover:text-[var(--ink-1)]"
          aria-label={t("search.clear")}
        >
          {t("search.clear")}
        </button>
      ) : null}
    </div>
  );
}
