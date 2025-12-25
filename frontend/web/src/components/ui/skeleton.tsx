export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-2xl bg-[var(--surface-2)]/70${
        className ? ` ${className}` : ""
      }`}
    />
  );
}
