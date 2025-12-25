"use client";

import React from "react";
import { classifyError } from "@/lib/errors";

type Props = {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
};

type State = { error: Error | null };

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    // Centralized place for observability hooks.
    // eslint-disable-next-line no-console
    console.error("Unhandled UI error:", error);
  }

  private reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;
    const normalized = classifyError(this.state.error);

    if (this.props.fallback) {
      return this.props.fallback(normalized, this.reset);
    }

    return (
      <div className="rounded-2xl border border-[var(--accent-error)]/40 bg-[var(--accent-error)]/10 p-4 text-sm text-[var(--accent-error)]">
        <p>Something went wrong.</p>
        <pre className="mt-2 whitespace-pre-wrap text-xs opacity-80">{normalized.message}</pre>
        <button
          type="button"
          className="mt-3 rounded-xl border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-2 text-xs text-[var(--ink-2)]"
          onClick={this.reset}
        >
          Retry
        </button>
      </div>
    );
  }
}

