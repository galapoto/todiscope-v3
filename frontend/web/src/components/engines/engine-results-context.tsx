"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type EngineResultKind = "run" | "report";

export type StoredEngineResult = {
  engineId: string;
  datasetVersionId: string;
  kind: EngineResultKind;
  recordedAt: string;
  payload: unknown;
};

type EngineResultsState = {
  results: StoredEngineResult[];
};

type EngineResultsContextValue = EngineResultsState & {
  record: (result: Omit<StoredEngineResult, "recordedAt">) => void;
  clearForDataset: (datasetVersionId: string) => void;
  clearAll: () => void;
  getLatest: (args: {
    engineId?: string;
    datasetVersionId?: string;
    kind?: EngineResultKind;
  }) => StoredEngineResult | undefined;
  getAllForDataset: (datasetVersionId: string) => StoredEngineResult[];
};

const EngineResultsContext = createContext<EngineResultsContextValue | undefined>(undefined);

const STORAGE_KEY = "todiscope.engineResults.v1";
const MAX_RESULTS = 50;

function loadState(): EngineResultsState {
  if (typeof window === "undefined") return { results: [] };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { results: [] };
    const parsed = JSON.parse(raw) as EngineResultsState;
    return { results: Array.isArray(parsed.results) ? parsed.results : [] };
  } catch {
    return { results: [] };
  }
}

function persist(state: EngineResultsState) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function EngineResultsProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<EngineResultsState>({ results: [] });

  useEffect(() => {
    setState(loadState());
  }, []);

  const record = useCallback((result: Omit<StoredEngineResult, "recordedAt">) => {
    const recordedAt = new Date().toISOString();
    setState((prev) => {
      const nextResults = [
        { ...result, recordedAt },
        ...prev.results.filter(
          (item) =>
            !(
              item.engineId === result.engineId &&
              item.datasetVersionId === result.datasetVersionId &&
              item.kind === result.kind
            )
        ),
      ].slice(0, MAX_RESULTS);
      const next = { results: nextResults };
      persist(next);
      return next;
    });
  }, []);

  const clearForDataset = useCallback((datasetVersionId: string) => {
    setState((prev) => {
      const next = { results: prev.results.filter((r) => r.datasetVersionId !== datasetVersionId) };
      persist(next);
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    const next = { results: [] };
    setState(next);
    persist(next);
  }, []);

  const getLatest = useCallback(
    (args: { engineId?: string; datasetVersionId?: string; kind?: EngineResultKind }) => {
      const { engineId, datasetVersionId, kind } = args;
      return state.results.find((result) => {
        if (engineId && result.engineId !== engineId) return false;
        if (datasetVersionId && result.datasetVersionId !== datasetVersionId) return false;
        if (kind && result.kind !== kind) return false;
        return true;
      });
    },
    [state.results]
  );

  const getAllForDataset = useCallback(
    (datasetVersionId: string) => state.results.filter((r) => r.datasetVersionId === datasetVersionId),
    [state.results]
  );

  const value = useMemo<EngineResultsContextValue>(
    () => ({
      ...state,
      record,
      clearForDataset,
      clearAll,
      getLatest,
      getAllForDataset,
    }),
    [state, record, clearForDataset, clearAll, getLatest, getAllForDataset]
  );

  return <EngineResultsContext.Provider value={value}>{children}</EngineResultsContext.Provider>;
}

export function useEngineResults() {
  const context = useContext(EngineResultsContext);
  if (!context) {
    throw new Error("useEngineResults must be used within EngineResultsProvider");
  }
  return context;
}

