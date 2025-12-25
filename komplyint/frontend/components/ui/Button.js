import Link from "next/link";

export default function Button({
  children,
  className = "",
  href,
  variant = "primary",
  ...props
}) {
  const base =
    "inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium transition";
  const styles =
    variant === "ghost"
      ? "border border-slate-200 text-slate-700 hover:bg-slate-50"
      : "bg-slate-900 text-white hover:bg-slate-800";

  const combined = `${base} ${styles} ${className}`.trim();

  if (href) {
    return (
      <Link className={combined} href={href} {...props}>
        {children}
      </Link>
    );
  }

  return (
    <button className={combined} type="button" {...props}>
      {children}
    </button>
  );
}
