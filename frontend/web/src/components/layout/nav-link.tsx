"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavLinkProps = {
  href: string;
  label: string;
  description: string;
  onboardId?: string;
};

export function NavLink({ href, label, description, onboardId }: NavLinkProps) {
  const pathname = usePathname();
  const active = pathname.startsWith(href);

  return (
    <Link
      href={href}
      data-onboard={onboardId}
      className={`group flex items-center justify-between rounded-2xl border px-4 py-3 text-sm transition ${
        active
          ? "border-[var(--accent-1)] bg-[var(--surface-2)] text-[var(--ink-1)] shadow-[0_16px_40px_rgba(15,118,110,0.18)]"
          : "border-transparent text-[var(--ink-2)] hover:border-[var(--surface-3)] hover:bg-[var(--surface-1)]"
      }`}
    >
      <span className="flex flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.2em]">
          {label}
        </span>
        <span className="text-sm text-[var(--ink-3)] group-hover:text-[var(--ink-2)]">
          {description}
        </span>
      </span>
      <span className="h-8 w-8 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] text-center text-xs leading-[2rem] text-[var(--ink-3)]">
        ↗
      </span>
    </Link>
  );
}
