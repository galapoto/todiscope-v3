"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useTranslation } from "react-i18next";
import { AuthGuard } from "@/components/auth/auth-guard";
import { useOnboarding } from "@/components/onboarding/onboarding-context";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-context";
import { OpenAIKeyInput } from "@/components/settings/openai-key-input";
import { useRouter } from "next/navigation";
import { useState, useRef } from "react";
import { getUserPhoto, setUserPhoto, removeUserPhoto } from "@/lib/user-photo-storage";
import { User, X } from "lucide-react";

export default function SettingsPage() {
  const { t } = useTranslation();
  const { start, resume, completed, active } = useOnboarding();
  const { role, token, email } = useAuth();
  const router = useRouter();
  const [userPhoto, setUserPhotoState] = useState<string | null>(getUserPhoto());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert(t("settings.profile.photoInvalid", { defaultValue: "Please select an image file" }));
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert(t("settings.profile.photoTooLarge", { defaultValue: "Image must be less than 5MB" }));
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setUserPhoto(dataUrl); // Save to storage
      setUserPhotoState(dataUrl); // Update UI state
    };
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = () => {
    removeUserPhoto();
    setUserPhotoState(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <AuthGuard>
      <AppShell title={t("settings.title")} subtitle={t("settings.subtitle")}>
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.profile.title", { defaultValue: "Profile" })}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.profile.body", { defaultValue: "Manage your profile photo and account settings." })}
            </p>
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-4">
                <div className="relative flex h-[120px] w-[120px] flex-shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[var(--surface-3)] bg-[var(--surface-2)]">
                  {userPhoto ? (
                    <img src={userPhoto} alt={email || "User"} className="h-full w-full object-cover" />
                  ) : (
                    <User className="h-[60px] w-[60px] text-[var(--ink-3)]" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[var(--ink-1)]">{email || "User"}</p>
                  <p className="text-xs text-[var(--ink-3)]">{role}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                  id="photo-upload"
                />
                <label
                  htmlFor="photo-upload"
                  className="cursor-pointer rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] px-4 py-2 text-sm font-medium text-[var(--ink-2)] transition hover:bg-[var(--surface-3)]"
                >
                  {t("settings.profile.upload", { defaultValue: "Upload Photo" })}
                </label>
                {userPhoto && (
                  <Button variant="secondary" size="sm" onClick={handleRemovePhoto}>
                    <X className="h-4 w-4" />
                    {t("settings.profile.remove", { defaultValue: "Remove" })}
                  </Button>
                )}
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.security.title")}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.security.body")}
            </p>
            <div className="mt-4 rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4 text-xs uppercase tracking-[0.2em] text-[var(--ink-3)]">
              {t("settings.security.role")}: {role}
            </div>
            {!token ? (
              <p className="mt-3 text-sm text-[var(--ink-3)]">
                {t("auth.required")}
              </p>
            ) : null}
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.onboarding.title")}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.onboarding.body")}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="primary"
                onClick={() => {
                  if (active) return;
                  if (completed) {
                    start();
                  } else {
                    resume();
                  }
                }}
              >
                {t("settings.onboarding.resume")}
              </Button>
              <Button variant="ghost" onClick={start}>
                {t("settings.onboarding.restart")}
              </Button>
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.openai.title", { defaultValue: "AI Configuration" })}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.openai.subtitle", {
                defaultValue: "Configure OpenAI API key for AI-powered insights and report generation.",
              })}
            </p>
            <div className="mt-4">
              <OpenAIKeyInput />
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.workflow.title", { defaultValue: "Workflow" })}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.workflow.body", {
                defaultValue: "Access workflow pages for data processing pipeline.",
              })}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => router.push("/workflow/import")}>
                {t("settings.workflow.import", { defaultValue: "Import" })}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => router.push("/workflow/normalize")}>
                {t("settings.workflow.normalize", { defaultValue: "Normalize" })}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => router.push("/workflow/calculate")}>
                {t("settings.workflow.calculate", { defaultValue: "Calculate" })}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => router.push("/workflow/report")}>
                {t("settings.workflow.report", { defaultValue: "Report" })}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => router.push("/workflow/audit")}>
                {t("settings.workflow.audit", { defaultValue: "Audit" })}
              </Button>
            </div>
          </section>

          <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
            <h3 className="text-base font-semibold text-[var(--ink-1)]">
              {t("settings.ocr.title", { defaultValue: "OCR Processing" })}
            </h3>
            <p className="mt-2 text-sm text-[var(--ink-3)]">
              {t("settings.ocr.body", {
                defaultValue: "Upload and process documents with OCR technology.",
              })}
            </p>
            <div className="mt-4">
              <Button variant="secondary" onClick={() => router.push("/ocr")}>
                {t("settings.ocr.open", { defaultValue: "Open OCR Page" })}
              </Button>
            </div>
          </section>

          <AuthGuard role="admin">
            <section className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
              <h3 className="text-base font-semibold text-[var(--ink-1)]">
                {t("settings.admin.title")}
              </h3>
              <p className="mt-2 text-sm text-[var(--ink-3)]">
                {t("settings.admin.body")}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => router.push("/coverage")}>
                  {t("settings.admin.coverage", { defaultValue: "Coverage Matrix" })}
                </Button>
              </div>
            </section>
          </AuthGuard>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
