"use client";

import { useDatasetVersions } from "@/hooks/use-dataset-versions";
import { useDatasetContext } from "@/components/data/dataset-context";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/lib/api-client";

export function DatasetSelector() {
  const { data, isLoading, isError, error } = useDatasetVersions();
  const { datasetVersionId, setDatasetVersionId, isLocked, selected, diff } = useDatasetContext();
  const { t } = useTranslation();

  const errorDetail = (() => {
    if (!isError) return null;
    if (error instanceof ApiError) {
      if (error.status === 401 || error.status === 403) {
        return t("datasets.restricted", {
          defaultValue: "Dataset listing is restricted. Check your permissions or API key.",
        });
      }
      if (error.status >= 500) {
        return t("datasets.unavailable", {
          defaultValue:
            "Dataset listing is unavailable (backend error). If running locally, configure the database connection.",
        });
      }
    }
    return t("states.error");
  })();

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
        {t("datasets.label")}
      </label>
      {selected ? (
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-[var(--ink-3)]">
          <span>
            {t("datasets.id")}: <span className="font-mono">{selected.id.slice(0, 8)}</span>
          </span>
          <span>
            {t("datasets.created")}: {new Date(selected.created_at).toLocaleString()}
          </span>
          {isLocked ? (
            <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px]">
              {t("datasets.locked", { defaultValue: "Locked" })}
            </span>
          ) : null}
          {diff?.kind === "different" ? (
            <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px]">
              {t("datasets.diff", { defaultValue: "Diff vs latest" })}
            </span>
          ) : null}
        </div>
      ) : null}
      <select
        value={datasetVersionId ?? ""}
        onChange={(event) => {
          const value = event.target.value;
          setDatasetVersionId(value ? value : null);
        }}
        data-onboard="dataset-selector"
        className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-3 py-2 text-xs text-[var(--ink-2)]"
        aria-invalid={Boolean(errorDetail)}
      >
        <option value="">{t("datasets.placeholder")}</option>
        {isLoading ? (
          <option value="" disabled>
            {t("states.loading")}
          </option>
        ) : errorDetail ? (
          <option value="" disabled>
            {errorDetail}
          </option>
        ) : (
          data?.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>
              {dataset.id.slice(0, 8)} · {new Date(dataset.created_at).toLocaleDateString()}
            </option>
          ))
        )}
      </select>
      {errorDetail ? (
        <p className="text-[10px] text-[var(--ink-3)]">{errorDetail}</p>
      ) : isLocked ? (
        <p className="text-[10px] text-[var(--ink-3)]">
          {t("datasets.readOnly", { defaultValue: "Historical dataset: read-only mode." })}
        </p>
      ) : null}
    </div>
  );
}
