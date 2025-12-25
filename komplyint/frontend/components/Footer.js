"use client";

import { Suspense } from "react";
import Link from "next/link";
import Container from "@/components/ui/Container";
import { useSearchParams } from "next/navigation";
import { getLanguage, getTranslations } from "@/lib/translations";

function FooterContent() {
  const searchParams = useSearchParams();
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  const legalLinks = [
    { href: "/privacy", label: t.footer.privacy },
    { href: "/terms", label: t.footer.terms },
    { href: "/cookies", label: t.footer.cookies },
  ];

  return (
    <footer className="border-t border-slate-200">
      <Container className="grid gap-6 py-10 text-sm text-slate-600 md:grid-cols-[1.5fr_1fr] md:items-center">
        <div className="space-y-3">
          <p className="text-base font-semibold text-slate-900">
            {t.footer.companyName}
          </p>
          <a className="text-slate-700 hover:text-slate-900" href="mailto:komplyint@komplying.com">
            komplyint@komplying.com
          </a>
          <p className="max-w-md text-xs text-slate-500">
            {t.footer.disclaimer}
          </p>
        </div>
        <div className="flex flex-wrap gap-6 md:justify-end">
          {legalLinks.map((link) => (
            <Link
              key={link.href}
              className="text-slate-700 transition hover:text-slate-900"
              href={`${link.href}?lang=${lang}`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </Container>
    </footer>
  );
}

export default function Footer() {
  return (
    <Suspense fallback={
      <footer className="border-t border-slate-200">
        <Container className="grid gap-6 py-10 text-sm text-slate-600 md:grid-cols-[1.5fr_1fr] md:items-center">
          <div className="space-y-3">
            <p className="text-base font-semibold text-slate-900">KOMPLYINT OY</p>
          </div>
        </Container>
      </footer>
    }>
      <FooterContent />
    </Suspense>
  );
}

