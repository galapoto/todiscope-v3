"use client";

import { Suspense } from "react";
import Link from "next/link";
import Container from "@/components/ui/Container";
import LanguageSwitcher from "./LanguageSwitcher";
import { useSearchParams } from "next/navigation";
import { getLanguage, getTranslations } from "@/lib/translations";

function HeaderContent() {
  const searchParams = useSearchParams();
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  const navLinks = [
    { href: "/what-we-do", label: t.nav.whatWeDo },
    { href: "/who-we-are", label: t.nav.whoWeAre },
    { href: "/contact", label: t.nav.contact },
  ];

  return (
    <header className="border-b border-slate-200">
      <Container className="flex items-center justify-between py-6">
        <Link className="text-lg font-semibold tracking-[0.2em]" href={`/?lang=${lang}`}>
          KOMPLYINT
        </Link>
        <div className="flex items-center gap-6">
          <nav className="flex items-center gap-6 text-sm" aria-label="Primary">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                className="text-slate-700 transition hover:text-slate-900"
                href={`${link.href}?lang=${lang}`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <LanguageSwitcher currentLang={lang} />
        </div>
      </Container>
    </header>
  );
}

export default function Header() {
  return (
    <Suspense fallback={
      <header className="border-b border-slate-200">
        <Container className="flex items-center justify-between py-6">
          <Link className="text-lg font-semibold tracking-[0.2em]" href="/">
            KOMPLYINT
          </Link>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-600">EN</span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-600">FI</span>
          </div>
        </Container>
      </header>
    }>
      <HeaderContent />
    </Suspense>
  );
}

