"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-context";

export function GoogleAuthButton() {
  const { t } = useTranslation();
  const { refreshSession } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Redirect to Google OAuth endpoint
      const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
      if (!clientId) {
        throw new Error("Google OAuth not configured. Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID.");
      }

      const redirectUri = `${window.location.origin}/api/auth/google/callback`;
      const scope = "openid email profile";
      const responseType = "code";
      const state = encodeURIComponent(window.location.href); // Return URL

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${new URLSearchParams({
        client_id: clientId,
        redirect_uri: redirectUri,
        response_type: responseType,
        scope,
        state,
      }).toString()}`;

      window.location.href = authUrl;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("auth.googleLoginFailed", { defaultValue: "Google login failed. Please try again." })
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <Button
        variant="primary"
        onClick={handleGoogleLogin}
        disabled={isLoading}
        className="w-full"
      >
        {isLoading
          ? t("auth.loading", { defaultValue: "Loading..." })
          : t("auth.signInWithGoogle", { defaultValue: "Sign in with Google" })}
      </Button>
      {error && (
        <p className="text-xs text-[var(--accent-error)]">{error}</p>
      )}
    </div>
  );
}



