"use client";

type TodiScopeLogoProps = {
  size?: number;
  showWordmark?: boolean;
  className?: string;
  wordmarkClassName?: string;
};

export function TodiScopeLogo({
  size = 48,
  showWordmark = false,
  className = "",
  wordmarkClassName = "hidden sm:inline",
}: TodiScopeLogoProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`.trim()}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        aria-label="TodiScope logo"
        role="img"
        suppressHydrationWarning
        className="text-blue-600 dark:text-blue-400"
      >
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke="currentColor"
          strokeWidth="3.5"
          className="opacity-90"
        />
        {/* T letter */}
        <line
          x1="22"
          y1="20"
          x2="42"
          y2="20"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          className="opacity-100"
        />
        <line
          x1="32"
          y1="20"
          x2="32"
          y2="30"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          className="opacity-100"
        />
        {/* S letter */}
        <path
          d="M 26 28 C 22 28, 22 34, 26 34 C 30 34, 30 40, 26 40"
          fill="none"
          stroke="currentColor"
          strokeWidth="3.5"
          strokeLinecap="round"
          className="opacity-100"
        />
        {/* Checkmark */}
        <polyline
          points="22,40 30,48 44,32"
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-100 drop-shadow-sm"
        />
      </svg>
      {showWordmark ? (
        <span
          className={`select-none text-lg font-semibold tracking-tight text-[var(--ink-1)] ${wordmarkClassName}`.trim()}
        >
          Todi<span className="text-[var(--accent-1)]">Scope</span>
        </span>
      ) : null}
    </div>
  );
}
