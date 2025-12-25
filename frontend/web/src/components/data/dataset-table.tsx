"use client";

import { useEffect, useMemo, useState } from "react";
import { useDatasetVersions } from "@/hooks/use-dataset-versions";
import { useTranslation } from "react-i18next";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/system/empty-state";
import { useSearch } from "@/components/search/search-context";
import { ApiError } from "@/lib/api-client";

type DatasetRow = {
  id: string;
  created_at: string;
};

export function DatasetTable() {
  const { t } = useTranslation();
  const { data = [], isLoading, isError, error } = useDatasetVersions();
  const { query, setQuery } = useSearch();
  const [globalFilter, setGlobalFilter] = useState(query);

  useEffect(() => {
    setGlobalFilter(query);
  }, [query]);

  const columns = useMemo<ColumnDef<DatasetRow>[]>(
    () => [
      {
        accessorKey: "id",
        header: () => t("datasets.id"),
        cell: ({ getValue }) => (
          <span className="font-semibold text-[var(--ink-1)]">
            {String(getValue()).slice(0, 12)}
          </span>
        ),
      },
      {
        accessorKey: "created_at",
        header: () => t("datasets.created"),
        cell: ({ getValue }) => (
          <span className="text-[var(--ink-3)]">
            {new Date(String(getValue())).toLocaleString()}
          </span>
        ),
      },
    ],
    [t]
  );

  const table = useReactTable({
    data,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 6 } },
  });

  const exportRows = table
    .getRowModel()
    .rows.map((row) => row.original);

  const errorMessage = (() => {
    if (!isError) return null;
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

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
          {t("states.loading", { defaultValue: "Loading..." })}
        </div>
      </div>
    );
  }

  if (isError && errorMessage) {
    return (
      <EmptyState
        title={t("states.error")}
        description={errorMessage}
      />
    );
  }

  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <input
            value={globalFilter}
            onChange={(event) => {
              setQuery(event.target.value);
              table.setPageIndex(0);
              setGlobalFilter(event.target.value);
            }}
            placeholder={t("datasets.search")}
            aria-label={t("datasets.search")}
            className="min-w-[200px] flex-1 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-4 py-2 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          />
        </div>
        <EmptyState
          title={t("states.empty")}
          description={t("datasets.noResults", { defaultValue: "No datasets found. Try adjusting your search filters." })}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          value={globalFilter}
          onChange={(event) => {
            setQuery(event.target.value);
            table.setPageIndex(0);
            setGlobalFilter(event.target.value);
          }}
          placeholder={t("datasets.search")}
          aria-label={t("datasets.search")}
          className="min-w-[200px] flex-1 rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] px-4 py-2 text-sm text-[var(--ink-2)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        />
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
          <span>{t("dashboard.table.page")}</span>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {t("dashboard.table.prev")}
          </Button>
          <span className="text-[var(--ink-2)]">
            {table.getState().pagination.pageIndex + 1}/{table.getPageCount() || 1}
          </span>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {t("dashboard.table.next")}
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
            {t("reports.exportExcel")}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={async () => {
              const XLSX = await import("xlsx");
              const worksheet = XLSX.utils.json_to_sheet(exportRows);
              const csv = XLSX.utils.sheet_to_csv(worksheet);
              const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
              const link = document.createElement("a");
              link.href = URL.createObjectURL(blob);
              link.download = "todiscope-datasets.csv";
              link.click();
              URL.revokeObjectURL(link.href);
            }}
            disabled={exportRows.length === 0}
          >
            {t("reports.exportCsv")}
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-[var(--surface-3)]">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--surface-2)] text-xs uppercase tracking-[0.2em] text-[var(--ink-3)]">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-4 py-3">
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {errorMessage ? (
              <tr>
                <td className="px-4 py-4 text-sm text-[var(--accent-error)]" colSpan={2}>
                  {errorMessage}
                </td>
              </tr>
            ) : table.getRowModel().rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-sm text-[var(--ink-3)]" colSpan={2}>
                  {t("states.empty")}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-[var(--surface-3)] bg-[var(--surface-1)]"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
