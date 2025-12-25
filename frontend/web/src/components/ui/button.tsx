"use client";

import { type ButtonHTMLAttributes } from "react";
import { useTranslation } from "react-i18next";

const variantClasses = {
  primary: "btn btn-primary",
  secondary: "btn btn-secondary",
  danger: "btn btn-danger",
  ghost: "btn btn-ghost",
} as const;

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variantClasses;
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const { t } = useTranslation();
  const sizeClass = `btn-${size}`;
  const classes = `${variantClasses[variant]} ${sizeClass}${
    className ? ` ${className}` : ""
  }`;
  return (
    <button
      {...props}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
          {t("buttons.loading")}
        </span>
      ) : (
        props.children
      )}
    </button>
  );
}
