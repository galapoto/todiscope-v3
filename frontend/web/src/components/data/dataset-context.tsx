"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useDatasetVersions } from "@/hooks/use-dataset-versions";

const STORAGE_KEY = "todiscope-dataset";

type DatasetContextValue = {
  datasetVersionId: string | null;
  setDatasetVersionId: (id: string | null) => void;
  /** Derived metadata for the selected dataset. */
  selected?: {
    id: string;
    created_at: string;
  };
  /** If true, the dataset should be treated as immutable/historical and therefore read-only. */
  isLocked: boolean;
  /** Diff indicator against the newest dataset version (if any). */
  diff?: {
    baseId: string;
    compareId: string;
    kind: "same" | "different";
  };
};

const DatasetContext = createContext<DatasetContextValue | null>(null);

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [datasetVersionId, setDatasetVersionIdState] = useState<string | null>(null);
  const { data: versions = [] } = useDatasetVersions();

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setDatasetVersionIdState(stored);
    }
  }, []);

  const setDatasetVersionId = (id: string | null) => {
    setDatasetVersionIdState(id);
    if (id) {
      window.localStorage.setItem(STORAGE_KEY, id);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  };

  const newest = versions[0];
  const selected = versions.find((v) => v.id === datasetVersionId);
  // Policy: only the newest dataset version is mutable.
  const isLocked = Boolean(datasetVersionId && newest && datasetVersionId !== newest.id);
  const diff: DatasetContextValue["diff"] =
    datasetVersionId && newest
      ? {
          baseId: newest.id,
          compareId: datasetVersionId,
          kind: (datasetVersionId === newest.id ? "same" : "different") as
            | "same"
            | "different",
        }
      : undefined;

  const value = useMemo(
    () => ({ datasetVersionId, setDatasetVersionId, selected, isLocked, diff }),
    [datasetVersionId, selected, isLocked, diff]
  );

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDatasetContext() {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error("useDatasetContext must be used within DatasetProvider");
  }
  return context;
}
