"use client";

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { EmptyState } from "@/components/system/empty-state";
import { useDatasetVersions } from "@/hooks/use-dataset-versions";
import { ApiError } from "@/lib/api-client";
import { useDatasetContext } from "@/components/data/dataset-context";

type DatasetRow = {
  id: string;
  created_at: string;
  is_read_only: boolean;
};

export function DataTable() {
  const { t } = useTranslation();
  const [globalFilter, setGlobalFilter] = useState("");
  const { datasetVersionId, setDatasetVersionId } = useDatasetContext();
  const datasetQuery = useDatasetVersions();

  const rowsData: DatasetRow[] = useMemo(() => {
    const versions = datasetQuery.data ?? [];
    const newestId = versions[0]?.id;
    return versions.map((v) => ({
      id: v.id,
      created_at: v.created_at,
      is_read_only: Boolean(newestId && v.id !== newestId),
    }));
  }, [datasetQuery.data]);

  const columns = useMemo<ColumnDef<DatasetRow>[]>(
    () => [
      {
        accessorKey: "id",
        header: () => t("datasets.id", { defaultValue: "Dataset" }),
        cell: ({ getValue }) => (
          <span className="font-semibold text-[var(--ink-1)]">
            {String(getValue()).slice(0, 12)}
          </span>
        ),
      },
      {
        accessorKey: "created_at",
        header: () => t("datasets.created", { defaultValue: "Imported" }),
        cell: ({ getValue }) => (
          <span className="text-[var(--ink-3)]">
            {new Date(String(getValue())).toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: "is_read_only",
        header: () => t("datasets.mode", { defaultValue: "Mode" }),
        cell: ({ getValue }) => (
          <span className="rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-1 text-xs font-semibold text-[var(--ink-2)]">
            {getValue<boolean>()
              ? t("datasets.readOnly", { defaultValue: "Read-only" })
              : t("datasets.mutable", { defaultValue: "Active" })}
          </span>
        ),
      },
      {
        id: "selected",
        header: () => t("datasets.selected", { defaultValue: "Selected" }),
        cell: ({ row }) =>
          row.original.id === datasetVersionId ? (
            <span className="rounded-full bg-[var(--accent-1)]/15 px-3 py-1 text-xs font-semibold text-[var(--accent-1)]">
              {t("states.active", { defaultValue: "Active" })}
            </span>
          ) : (
            <span className="text-[var(--ink-3)]">—</span>
          ),
      },
    ],
    [datasetVersionId, t]
  );

  const table = useReactTable({
    data: rowsData,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: 6 },
    },
  });

  const exportRows = table.getRowModel().rows.map((row) => row.original);

  const errorMessage = (() => {
    if (!datasetQuery.isError) return null;
    const error = datasetQuery.error;
    if (error instanceof ApiError) {
      if (error.status === 401 || error.status === 403) {
        return t("datasets.restricted", {
          defaultValue: "Datasets exist but are restricted. Check your permissions or API key.",
        });
      }
      if (error.status >= 500) {
        return t("datasets.unavailable", {
          defaultValue:
            "Datasets are temporarily unavailable (backend error). If running locally, configure the database connection.",
        });
      }
    }
    return t("states.error");
  })();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          value={globalFilter ?? ""}
          onChange={(event) => {
            table.setPageIndex(0);
            setGlobalFilter(event.target.value);
          }}
          placeholder={t("datasets.search", { defaultValue: "Search datasets..." })}
          aria-label={t("datasets.search", { defaultValue: "Search datasets" })}
          className="min-w-[200px] flex-1 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-4 py-2 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        />
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
          <span>{t("dashboard.table.page", { defaultValue: "Page" })}</span>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {t("dashboard.table.prev", { defaultValue: "Prev" })}
          </Button>
          <span className="text-[var(--ink-2)]">
            {table.getState().pagination.pageIndex + 1}/{table.getPageCount()}
          </span>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {t("dashboard.table.next", { defaultValue: "Next" })}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={async () => {
              const XLSX = await import("xlsx");
              const workbook = XLSX.utils.book_new();
              const worksheet = XLSX.utils.json_to_sheet(exportRows);
              XLSX.utils.book_append_sheet(workbook, worksheet, "Datasets");
              XLSX.writeFile(workbook, "todiscope-datasets.xlsx");
            }}
            disabled={exportRows.length === 0}
          >
            {t("reports.exportExcel", { defaultValue: "Export Excel" })}
          </Button>
        </div>
      </div>
      {datasetQuery.isError ? (
        <EmptyState
          title={t("states.error", { defaultValue: "Error" })}
          description={errorMessage ?? t("states.error", { defaultValue: "Error" })}
        />
      ) : null}
      <div className="overflow-x-auto rounded-2xl border border-[var(--surface-3)]">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--surface-2)] text-xs uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-4 py-3">
                    {header.isPlaceholder ? null : (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className="flex items-center gap-2"
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getIsSorted() ? (
                          <span className="text-[var(--accent-1)]">
                            {header.column.getIsSorted() === "asc" ? "↑" : "↓"}
                          </span>
                        ) : null}
                      </button>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
        </table>
        <div className="border-t border-[var(--surface-3)]">
          {datasetQuery.isLoading ? (
            <div className="px-4 py-8 text-sm text-[var(--ink-3)]">
              {t("states.loading", { defaultValue: "Loading..." })}
            </div>
          ) : datasetQuery.isError ? (
            <div className="px-4 py-8">
              <EmptyState
                title={t("states.error", { defaultValue: "Error" })}
                description={errorMessage ?? t("states.error", { defaultValue: "Error" })}
              />
            </div>
          ) : table.getRowModel().rows.length === 0 ? (
            <div className="px-4 py-8">
              <EmptyState
                title={t("states.empty", { defaultValue: "Empty" })}
                description={t("datasets.empty", {
                  defaultValue: "No dataset has been imported yet. Import a dataset to unlock engines and reports.",
                })}
              />
            </div>
          ) : (
            <div className="max-h-[220px] overflow-y-auto">
              {table.getRowModel().rows.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setDatasetVersionId(row.original.id)}
                  className={`grid w-full grid-cols-4 border-b border-[var(--surface-3)] px-4 py-3 text-left text-sm transition ${
                    row.original.id === datasetVersionId
                      ? "bg-[var(--accent-1)]/10 text-[var(--ink-1)]"
                      : "bg-[var(--surface-1)] text-[var(--ink-2)] hover:bg-[var(--surface-2)]"
                  }`}
                  aria-label={t("datasets.select", {
                    defaultValue: "Select dataset {{id}}",
                    id: row.original.id,
                  })}
                >
                  {row.getVisibleCells().map((cell) => (
                    <span key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </span>
                  ))}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
