"use client";

import React from "react";

type TodiScopeLogoProps = {
  /** Height of the icon circle in px */
  size?: number;
  /** Show or hide the "TodiScope" wordmark */
  showWordmark?: boolean;
  /** Variant for compatibility (ignored) */
  variant?: "A" | "B" | "C";
  /** Mode for compatibility (ignored) */
  mode?: "light" | "dark";
  /** Additional CSS classes */
  className?: string;
};

const LIGHT_BLUE = "#60a5fa";  // brighter blue for T/S (slate-400 blue)
const WHITE = "#ffffff";  // white for circle and checkmark
const ACCENT_BLUE = "#2563eb";  // accent blue

export default function TodiScopeLogo({
  size = 32,
  showWordmark = false,
  variant,
  mode,
  className = "",
}: TodiScopeLogoProps) {
  const iconSize = size;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 64 64"
        aria-label="TodiScope logo"
        role="img"
      >
        {/* Outer circle */}
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke={WHITE}
          strokeWidth="3.5"
          opacity="1"
        />

        {/* Stylised "T" (top bar + stem) */}
        <line
          x1="22"
          y1="20"
          x2="42"
          y2="20"
          stroke={LIGHT_BLUE}
          strokeWidth="4"
          strokeLinecap="round"
          opacity="0.9"
        />
        <line
          x1="32"
          y1="20"
          x2="32"
          y2="30"
          stroke={LIGHT_BLUE}
          strokeWidth="4"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* Simplified "S" hugging the stem of the T */}
        <path
          d="
            M 26 28
            C 22 28, 22 34, 26 34
            C 30 34, 30 40, 26 40
          "
          fill="none"
          stroke={LIGHT_BLUE}
          strokeWidth="3.5"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* Checkmark */}
        <polyline
          points="22,40 30,48 44,32"
          fill="none"
          stroke={WHITE}
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {showWordmark && (
        <span className="select-none text-2xl font-semibold tracking-tight text-slate-100">
          Todi<span className="text-blue-400">Scope</span>
        </span>
      )}
    </div>
  );
}
