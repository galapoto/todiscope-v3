import { type HTMLAttributes } from "react";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  variant?: "surface" | "muted";
  resizable?: boolean;
  hoverable?: boolean;
};

const variantClasses = {
  surface: "border-[var(--surface-3)] bg-[var(--surface-1)]",
  muted: "border-[var(--surface-3)] bg-[var(--surface-2)]",
} as const;

export function Card({
  variant = "surface",
  resizable = false,
  hoverable = false,
  className,
  ...props
}: CardProps) {
  const classes = `rounded-2xl border ${variantClasses[variant]}${
    hoverable ? " card-hover" : ""
  }${resizable ? " resize-y overflow-auto" : ""}${className ? ` ${className}` : ""}`;
  return <div {...props} className={classes} />;
}
