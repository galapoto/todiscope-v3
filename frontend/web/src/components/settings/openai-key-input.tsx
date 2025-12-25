"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  getOpenAIKey,
  setOpenAIKey,
  clearOpenAIKey,
  hasOpenAIKey,
  validateOpenAIKeyFormat,
} from "@/lib/openai-storage";

export function OpenAIKeyInput() {
  const { t } = useTranslation();
  const [key, setKey] = useState("");
  const [isVisible, setIsVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const existing = getOpenAIKey();
    if (existing) {
      setKey(existing);
      setSaved(true);
    }
  }, []);

  const handleSave = () => {
    setError(null);
    if (!key.trim()) {
      setError(t("settings.openai.keyRequired", { defaultValue: "API key is required." }));
      return;
    }
    if (!validateOpenAIKeyFormat(key.trim())) {
      setError(
        t("settings.openai.invalidFormat", {
          defaultValue: "Invalid API key format. OpenAI keys start with 'sk-'.",
        })
      );
      return;
    }
    try {
      setOpenAIKey(key.trim());
      setSaved(true);
      setIsVisible(false);
    } catch (err) {
      setError(
        t("settings.openai.saveFailed", {
          defaultValue: "Failed to save API key. Check browser storage permissions.",
        })
      );
    }
  };

  const handleClear = () => {
    if (confirm(t("settings.openai.confirmClear", { defaultValue: "Clear API key?" }))) {
      clearOpenAIKey();
      setKey("");
      setSaved(false);
      setIsVisible(false);
      setError(null);
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-[var(--ink-2)]">
          {t("settings.openai.label", { defaultValue: "OpenAI API Key" })}
        </label>
        <p className="mt-1 text-xs text-[var(--ink-3)]">
          {t("settings.openai.description", {
            defaultValue: "Required for AI insights and report generation. Stored securely in browser storage.",
          })}
        </p>
      </div>

      {saved && !isVisible ? (
        <div className="flex items-center gap-3">
          <div className="flex-1 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-sm">
            <span className="text-[var(--ink-3)]">
              {t("settings.openai.keySaved", { defaultValue: "API key saved" })}
            </span>
            <span className="ml-2 text-[var(--accent-success)]">✓</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => setIsVisible(true)}>
            {t("settings.openai.edit", { defaultValue: "Edit" })}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClear}>
            {t("settings.openai.clear", { defaultValue: "Clear" })}
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type={isVisible ? "text" : "password"}
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setError(null);
                setSaved(false);
              }}
              placeholder={t("settings.openai.placeholder", { defaultValue: "sk-..." })}
              className="flex-1 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-2 text-sm text-[var(--ink-1)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              aria-label={t("settings.openai.label", { defaultValue: "OpenAI API Key" })}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsVisible(!isVisible)}
              aria-label={isVisible ? "Hide key" : "Show key"}
            >
              {isVisible ? "👁️" : "👁️‍🗨️"}
            </Button>
          </div>
          {error && (
            <p className="text-xs text-[var(--accent-error)]">{error}</p>
          )}
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={handleSave}>
              {t("settings.openai.save", { defaultValue: "Save" })}
            </Button>
            {saved && (
              <Button variant="ghost" size="sm" onClick={() => setIsVisible(false)}>
                {t("settings.openai.cancel", { defaultValue: "Cancel" })}
              </Button>
            )}
          </div>
        </div>
      )}

      {!hasOpenAIKey() && (
        <p className="text-xs text-[var(--accent-warning)]">
          {t("settings.openai.warning", {
            defaultValue: "AI features will be disabled until an API key is provided.",
          })}
        </p>
      )}
    </div>
  );
}



