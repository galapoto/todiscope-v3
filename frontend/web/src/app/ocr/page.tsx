"use client";

import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";
import { useTranslation } from "react-i18next";
import { OCRUpload } from "@/components/ocr/ocr-upload";

export default function OCRPage() {
  const { t } = useTranslation();
  return (
    <AuthGuard>
      <AppShell
        title={t("ocr.title", { defaultValue: "OCR Upload" })}
        subtitle={t("ocr.subtitle", { defaultValue: "Upload and process documents with OCR" })}
      >
        <div className="rounded-3xl border border-[var(--surface-3)] bg-[var(--surface-1)] p-6">
          <OCRUpload
            onUploadComplete={(result) => {
              console.log("OCR result:", result);
            }}
          />
        </div>
      </AppShell>
    </AuthGuard>
  );
}


