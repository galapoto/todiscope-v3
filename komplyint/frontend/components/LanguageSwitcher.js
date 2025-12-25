"use client";

import Link from "next/link";
import { useSearchParams, usePathname } from "next/navigation";

export default function LanguageSwitcher({ currentLang }) {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const createUrl = (lang) => {
    const params = new URLSearchParams(searchParams?.toString() || "");
    params.set("lang", lang);
    return `${pathname}?${params.toString()}`;
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <Link
        href={createUrl("en")}
        className={currentLang === "en" ? "font-semibold text-slate-900" : "text-slate-600 hover:text-slate-900"}
      >
        EN
      </Link>
      <span className="text-slate-400">|</span>
      <Link
        href={createUrl("fi")}
        className={currentLang === "fi" ? "font-semibold text-slate-900" : "text-slate-600 hover:text-slate-900"}
      >
        FI
      </Link>
    </div>
  );
}

