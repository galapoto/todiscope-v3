"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export type AIContext = {
  engine?: string;
  dataset?: string;
  report?: string;
  finding?: string;
};

type AIPanelProps = {
  context?: AIContext;
  initialInsight?: string;
  onQuery?: (query: string, context: AIContext) => Promise<string>;
  readOnly?: boolean;
  evidenceIds?: string[];
};

export function AIPanel({
  context = {},
  initialInsight,
  onQuery,
  readOnly = false,
  evidenceIds = [],
}: AIPanelProps) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<Array<{ role: "ai" | "user"; content: string }>>(
    initialInsight ? [{ role: "ai", content: initialInsight }] : []
  );
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !onQuery || isProcessing) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsProcessing(true);

    try {
      const response = await onQuery(userMessage, context);
      setMessages((prev) => [...prev, { role: "ai", content: response }]);
    } catch (error) {
      console.error("AI query failed:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: t("ai.error", { defaultValue: "Sorry, I encountered an error processing your query." }),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const handleExport = () => {
    const content = messages.map((m) => `${m.role === "ai" ? "AI" : "User"}: ${m.content}`).join("\n\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-conversation-${new Date().toISOString().split("T")[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getContextLabel = () => {
    const parts: string[] = [];
    if (context.engine) parts.push(t("ai.context.engine", { engine: context.engine }));
    if (context.dataset) parts.push(t("ai.context.dataset", { dataset: context.dataset }));
    if (context.report) parts.push(t("ai.context.report", { report: context.report }));
    if (context.finding) parts.push(t("ai.context.finding", { finding: context.finding }));
    return parts.length > 0 ? parts.join(" • ") : t("ai.context.global");
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-1)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--surface-3)] p-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--ink-1)]">{t("ai.title")}</h3>
          <p className="text-xs text-[var(--ink-3)]">{getContextLabel()}</p>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={handleExport}>
            {t("ai.export")}
          </Button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center">
            <div className="text-[var(--ink-3)]">
              <p className="mb-2 text-sm font-medium">{t("ai.empty.title")}</p>
              <p className="text-xs">{t("ai.empty.description")}</p>
            </div>
          </div>
        )}
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role === "ai" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-1)]/15 text-sm font-semibold text-[var(--accent-1)]">
                AI
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl p-3 ${
                message.role === "user"
                  ? "bg-[var(--accent-1)] text-[var(--surface-1)]"
                  : "bg-[var(--surface-2)] text-[var(--ink-1)]"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              {message.role === "ai" && evidenceIds.length > 0 && (
                <p className="mt-2 text-xs opacity-75">
                  {t("ai.basedOnEvidence", { count: evidenceIds.length })}
                </p>
              )}
              <button
                type="button"
                onClick={() => handleCopy(message.content)}
                className="mt-2 text-xs opacity-60 hover:opacity-100"
              >
                {copied ? t("ai.copied") : t("ai.copy")}
              </button>
            </div>
            {message.role === "user" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--surface-2)] text-sm font-semibold text-[var(--ink-2)]">
                U
              </div>
            )}
          </div>
        ))}
        {isProcessing && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-1)]/15 text-sm font-semibold text-[var(--accent-1)]">
              AI
            </div>
            <div className="rounded-2xl bg-[var(--surface-2)] p-3">
              <div className="flex gap-1">
                <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--ink-3)] [animation-delay:0ms]" />
                <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--ink-3)] [animation-delay:150ms]" />
                <div className="h-2 w-2 animate-bounce rounded-full bg-[var(--ink-3)] [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {!readOnly && onQuery && (
        <form onSubmit={handleSubmit} className="border-t border-[var(--surface-3)] p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t("ai.inputPlaceholder")}
              className="flex-1 rounded-lg border border-[var(--surface-3)] bg-[var(--surface-1)] px-4 py-2 text-sm text-[var(--ink-1)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              disabled={isProcessing}
            />
            <Button type="submit" variant="primary" disabled={!input.trim() || isProcessing}>
              {t("ai.send")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}



