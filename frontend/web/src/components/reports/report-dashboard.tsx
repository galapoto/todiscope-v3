"use client";

import {
  Bar,
  BarChart,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Legend,
} from "recharts";
import { useMemo } from "react";

type ChartKind = "bar" | "line" | "pie" | "histogram";

type ChartBlock = {
  id: string;
  title: string;
  kind: ChartKind;
  data: Array<Record<string, string | number>>;
  xKey?: string;
  yKey?: string;
};

type Metric = {
  label: string;
  value: string | number;
};

const pieColors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"];

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value.replace(/,/g, ""));
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function pickLabel(obj: Record<string, unknown>): string | null {
  const candidates = ["name", "label", "category", "typology", "metric", "framework", "bucket"];
  for (const key of candidates) {
    const value = obj[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

function pickXKey(obj: Record<string, unknown>): string | null {
  const candidates = ["date", "timestamp", "period", "month", "year"];
  for (const key of candidates) {
    const value = obj[key];
    if (typeof value === "string" && value.trim()) return key;
  }
  return null;
}

function extractMetrics(report: unknown): Metric[] {
  if (!report || typeof report !== "object") return [];
  const root = report as Record<string, unknown>;
  const sections = ["executive_summary", "summary", "totals"];
  const metrics: Metric[] = [];

  for (const section of sections) {
    const block = root[section];
    if (!block || typeof block !== "object") continue;
    for (const [key, value] of Object.entries(block as Record<string, unknown>)) {
      const num = toNumber(value);
      if (num === null) continue;
      metrics.push({ label: key.replace(/_/g, " "), value: num });
    }
  }

  if (metrics.length > 0) return metrics.slice(0, 6);
  return [];
}

function extractPieFromObject(obj: Record<string, unknown>, title: string): ChartBlock | null {
  const entries = Object.entries(obj)
    .map(([key, value]) => ({ name: key.replace(/_/g, " "), value: toNumber(value) }))
    .filter((item) => item.value !== null) as Array<{ name: string; value: number }>;

  if (entries.length < 2 || entries.length > 8) return null;
  return {
    id: `pie-${title}`,
    title,
    kind: "pie",
    data: entries,
    xKey: "name",
    yKey: "value",
  };
}

function histogram(values: number[], title: string): ChartBlock | null {
  if (values.length < 3) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  if (min === max) return null;
  const bins = Math.min(8, Math.max(4, Math.floor(Math.sqrt(values.length))));
  const step = (max - min) / bins;
  const buckets = new Array(bins).fill(0).map((_, i) => ({
    bucket: `${(min + step * i).toFixed(1)} - ${(min + step * (i + 1)).toFixed(1)}`,
    value: 0,
  }));
  values.forEach((value) => {
    const idx = Math.min(bins - 1, Math.floor((value - min) / step));
    buckets[idx].value += 1;
  });
  return {
    id: `hist-${title}`,
    title,
    kind: "histogram",
    data: buckets,
    xKey: "bucket",
    yKey: "value",
  };
}

function extractCharts(report: unknown): ChartBlock[] {
  if (!report || typeof report !== "object") return [];
  const root = report as Record<string, unknown>;
  const charts: ChartBlock[] = [];

  const scanObject = (obj: Record<string, unknown>, prefix: string) => {
    const pie = extractPieFromObject(obj, prefix);
    if (pie) charts.push(pie);
    for (const [key, value] of Object.entries(obj)) {
      if (Array.isArray(value)) {
        scanArray(value, `${prefix}: ${key}`);
      } else if (value && typeof value === "object") {
        const nestedPie = extractPieFromObject(value as Record<string, unknown>, `${prefix}: ${key}`);
        if (nestedPie) charts.push(nestedPie);
      }
    }
  };

  const scanArray = (arr: unknown[], title: string) => {
    const objects = arr.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
    if (objects.length === 0) {
      const numbers = arr.map(toNumber).filter((v): v is number => v !== null);
      const hist = histogram(numbers, title);
      if (hist) charts.push(hist);
      return;
    }

    const sample = objects[0];
    const xKey = pickXKey(sample);
    const labelKey = pickLabel(sample);
    const numericKeys = Object.keys(sample).filter((key) => toNumber(sample[key]) !== null);
    const yKey = numericKeys.find((key) => key !== xKey);
    if (!yKey) return;

    if (xKey) {
      const data = objects
        .map((item) => ({
          [xKey]: String(item[xKey]),
          [yKey]: toNumber(item[yKey]) ?? 0,
        }))
        .slice(0, 40);
      charts.push({
        id: `line-${title}`,
        title,
        kind: "line",
        data,
        xKey,
        yKey,
      });
      return;
    }

    if (labelKey) {
      const data = objects
        .map((item) => ({
          name: String(item[labelKey]),
          value: toNumber(item[yKey]) ?? 0,
        }))
        .slice(0, 16);
      charts.push({
        id: `bar-${title}`,
        title,
        kind: "bar",
        data,
        xKey: "name",
        yKey: "value",
      });
    }

    objects.forEach((item) => {
      for (const [key, value] of Object.entries(item)) {
        if (Array.isArray(value)) {
          scanArray(value, `${title}: ${key}`);
        } else if (value && typeof value === "object") {
          scanObject(value as Record<string, unknown>, `${title}: ${key}`);
        }
      }
    });
  };

  const scan = (value: unknown, title: string) => {
    if (Array.isArray(value)) {
      scanArray(value, title);
      return;
    }
    if (value && typeof value === "object") {
      scanObject(value as Record<string, unknown>, title);
      for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
        if (Array.isArray(child)) scanArray(child, `${title}: ${key}`);
      }
    }
  };

  for (const [key, value] of Object.entries(root)) {
    scan(value, key.replace(/_/g, " "));
  }

  return charts.slice(0, 8);
}

export function ReportDashboard({ report }: { report: unknown }) {
  const metrics = useMemo(() => extractMetrics(report), [report]);
  const charts = useMemo(() => extractCharts(report), [report]);

  return (
    <div className="space-y-6">
      {metrics.length ? (
        <div className="grid gap-4 md:grid-cols-3">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {metric.label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-[var(--ink-1)]">
                {metric.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {charts.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {charts.map((chart) => (
            <div
              key={chart.id}
              className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
                {chart.title}
              </p>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  {chart.kind === "bar" ? (
                    <BarChart data={chart.data}>
                      <XAxis dataKey={chart.xKey} stroke="var(--ink-3)" fontSize={10} />
                      <YAxis stroke="var(--ink-3)" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface-1)",
                          borderRadius: 12,
                          borderColor: "var(--surface-3)",
                          color: "var(--ink-1)",
                        }}
                      />
                      <Bar dataKey={chart.yKey} fill="var(--chart-2)" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  ) : chart.kind === "line" ? (
                    <LineChart data={chart.data}>
                      <XAxis dataKey={chart.xKey} stroke="var(--ink-3)" fontSize={10} />
                      <YAxis stroke="var(--ink-3)" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface-1)",
                          borderRadius: 12,
                          borderColor: "var(--surface-3)",
                          color: "var(--ink-1)",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey={chart.yKey}
                        stroke="var(--chart-1)"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  ) : chart.kind === "pie" ? (
                    <PieChart>
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface-1)",
                          borderRadius: 12,
                          borderColor: "var(--surface-3)",
                          color: "var(--ink-1)",
                        }}
                      />
                      <Legend />
                      <Pie data={chart.data} dataKey={chart.yKey} nameKey={chart.xKey} innerRadius={30} outerRadius={70}>
                        {chart.data.map((entry, index) => (
                          <Cell key={String(entry[chart.xKey ?? "name"])} fill={pieColors[index % pieColors.length]} />
                        ))}
                      </Pie>
                    </PieChart>
                  ) : (
                    <BarChart data={chart.data}>
                      <XAxis dataKey={chart.xKey} stroke="var(--ink-3)" fontSize={10} />
                      <YAxis stroke="var(--ink-3)" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface-1)",
                          borderRadius: 12,
                          borderColor: "var(--surface-3)",
                          color: "var(--ink-1)",
                        }}
                      />
                      <Bar dataKey={chart.yKey} fill="var(--chart-4)" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-[var(--surface-3)] bg-[var(--surface-2)] p-6 text-sm text-[var(--ink-3)]">
          No chartable data detected for this report.
        </div>
      )}
    </div>
  );
}
