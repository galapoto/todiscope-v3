"use client";

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-4 text-sm text-[var(--ink-2)]">
      <p className="font-semibold">{title}</p>
      {description ? <p className="mt-1 text-xs text-[var(--ink-3)]">{description}</p> : null}
    </div>
  );
}

