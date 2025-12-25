"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-context";
import { AuthScreen } from "@/components/auth/auth-screen";
import { GoogleAuthButton } from "@/components/auth/google-auth-button";

export default function LoginPage() {
  const { t } = useTranslation();

  return (
    <AuthScreen title={t("auth.loginTitle")} subtitle={t("auth.subtitle")}>
      <Suspense
        fallback={
          <div className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-sm text-[var(--ink-3)]">
            {t("states.loading", { defaultValue: "Loading..." })}
          </div>
        }
      >
        <LoginForm />
      </Suspense>
    </AuthScreen>
  );
}

function LoginForm() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--ink-3)]">
          {t("auth.subtitle")}
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-[var(--ink-1)]">
          {t("auth.loginTitle")}
        </h2>
      </div>

      <form
        className="space-y-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(null);
          setLoading(true);
          try {
            await login(email, password);
            const next = params.get("next") || "/dashboard";
            router.replace(next);
          } catch (err) {
            const message = err instanceof Error ? err.message : "";
            setError(message || t("auth.loginFailed"));
          } finally {
            setLoading(false);
          }
        }}
      >
        <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
          {t("auth.email")}
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          />
        </label>
        <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
          {t("auth.password")}
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            className="rounded-xl border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          />
        </label>

        {error ? (
          <p className="rounded-xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-3 text-sm text-[var(--accent-error)]">
            {error}
          </p>
        ) : null}

        <div className="grid gap-2">
          <Button variant="primary" loading={loading} type="submit">
            {t("auth.signIn")}
          </Button>
          <GoogleAuthButton />
        </div>
      </form>
    </div>
  );
}
