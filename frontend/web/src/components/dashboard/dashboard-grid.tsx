"use client";

import { useMemo, useState, useCallback, useEffect, useRef } from "react";
import { ResponsiveGridLayout } from "react-grid-layout";
import type { Layout } from "react-grid-layout";

type GridLayout = {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  static?: boolean;
  minW?: number;
  minH?: number;
};
import { DashboardOverview } from "@/components/dashboard/dashboard-overview";
import { RealtimeMetrics } from "@/components/dashboard/realtime-metrics";
import { AIReportWidget } from "@/components/dashboard/ai-report-widget";
import { InsightStream } from "@/components/dashboard/insight-stream";
import { EngineStatusWidget } from "@/components/widgets/engine-status-widget";
import dynamic from "next/dynamic";
import { WidgetShell } from "@/components/dashboard/widget-shell";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

const ChartsPanel = dynamic(
  () => import("@/components/dashboard/charts-panel").then((mod) => mod.ChartsPanel),
  { ssr: false }
);
const DataTable = dynamic(
  () => import("@/components/data/data-table").then((mod) => mod.DataTable),
  { ssr: false }
);

type WidgetConfig = {
  id: string;
  titleKey: string;
  subtitleKey: string;
  content: React.ReactNode;
};

// Initial widget configuration
const initialWidgets: WidgetConfig[] = [
  {
    id: "overview",
    titleKey: "dashboard.widgets.financialMetrics",
    subtitleKey: "dashboard.widgets.financialMetricsSubtitle",
    content: <DashboardOverview />,
  },
  {
    id: "realtime",
    titleKey: "dashboard.widgets.realtime",
    subtitleKey: "dashboard.widgets.realtimeSubtitle",
    content: <RealtimeMetrics />,
  },
  {
    id: "insights",
    titleKey: "dashboard.widgets.auditTimeline",
    subtitleKey: "dashboard.widgets.auditTimelineSubtitle",
    content: <InsightStream />,
  },
  {
    id: "charts",
    titleKey: "dashboard.widgets.exposureBreakdown",
    subtitleKey: "dashboard.widgets.exposureBreakdownSubtitle",
    content: <ChartsPanel />,
  },
  {
    id: "report",
    titleKey: "dashboard.widgets.report",
    subtitleKey: "dashboard.widgets.reportSubtitle",
    content: <AIReportWidget />,
  },
  {
    id: "engines",
    titleKey: "dashboard.widgets.engines",
    subtitleKey: "dashboard.widgets.enginesSubtitle",
    content: <EngineStatusWidget />,
  },
  {
    id: "table",
    titleKey: "dashboard.widgets.table",
    subtitleKey: "dashboard.widgets.tableSubtitle",
    content: <DataTable />,
  },
];

// Base layout configuration
const baseLayout: GridLayout[] = [
  { i: "overview", x: 0, y: 0, w: 6, h: 10, minW: 4, minH: 8 },
  { i: "realtime", x: 6, y: 0, w: 6, h: 10, minW: 4, minH: 8 },
  { i: "insights", x: 0, y: 10, w: 4, h: 10, minW: 3, minH: 8 },
  { i: "charts", x: 4, y: 10, w: 8, h: 10, minW: 4, minH: 8 },
  { i: "report", x: 0, y: 20, w: 6, h: 12, minW: 4, minH: 10 },
  { i: "engines", x: 6, y: 20, w: 6, h: 12, minW: 4, minH: 10 },
  { i: "table", x: 0, y: 32, w: 12, h: 12, minW: 6, minH: 10 },
];

const colsByBreakpoint = { lg: 12, md: 12, sm: 1, xs: 1 };

const STORAGE_KEY = "todiscope-dashboard-layout";
const STORAGE_VERSION = 2;

type StoredLayoutState = {
  version: number;
  layouts: { lg: GridLayout[]; md: GridLayout[]; sm: GridLayout[]; xs: GridLayout[] };
  widgets: string[];
  pinned: Record<string, boolean>;
};

type BreakpointLayouts = StoredLayoutState["layouts"];

const minById = baseLayout.reduce<Record<string, { minW: number; minH: number }>>(
  (acc, item) => {
    acc[item.i] = { minW: item.minW ?? 1, minH: item.minH ?? 2 };
    return acc;
  },
  {}
);

// Helper function to filter layouts by available widget IDs
const filterLayoutsByWidgetIds = (
  layouts: GridLayout[],
  widgetIds: Set<string>
): GridLayout[] => {
  return layouts.filter((layout) => widgetIds.has(layout.i));
};

function normalizeBreakpointLayout(
  layouts: GridLayout[] | undefined,
  widgetIds: Set<string>,
  breakpoint: keyof typeof colsByBreakpoint
): GridLayout[] {
  const cols = colsByBreakpoint[breakpoint] ?? 12;
  const filtered = filterLayoutsByWidgetIds(layouts ?? [], widgetIds);

  return filtered.map((item) => {
    if (breakpoint === "sm" || breakpoint === "xs") {
      const mins = minById[item.i] ?? { minW: 1, minH: 2 };
      return {
        ...item,
        x: 0,
        w: 1,
        h: Math.max(mins.minH, item.h),
        minW: 1,
        minH: mins.minH,
      };
    }

    const mins = minById[item.i] ?? { minW: 1, minH: 2 };
    const nextW = Math.max(mins.minW, Math.min(item.w, cols));
    const nextH = Math.max(mins.minH, item.h);
    const nextX = Math.max(0, Math.min(item.x, cols - nextW));
    return {
      ...item,
      x: nextX,
      w: nextW,
      h: nextH,
      minW: mins.minW,
      minH: mins.minH,
    };
  });
}

function looksCollapsed(layout: GridLayout[] | undefined): boolean {
  if (!layout || layout.length === 0) return false;
  const tinyCount = layout.filter((item) => item.w <= 1 || item.h <= 2).length;
  return tinyCount >= Math.ceil(layout.length / 2);
}

function hasUnknownWidgets(layout: GridLayout[] | undefined): boolean {
  if (!layout || layout.length === 0) return false;
  return layout.some((item) => !minById[item.i]);
}

function isInvalidLayouts(layouts: BreakpointLayouts | undefined): boolean {
  if (!layouts) return true;
  const candidates: Array<GridLayout[] | undefined> = [
    layouts.lg,
    layouts.md,
    layouts.sm,
    layouts.xs,
  ];
  return candidates.some((layout) => hasUnknownWidgets(layout) || looksCollapsed(layout));
}

// Helper function to generate responsive layouts based on available widgets
const generateResponsiveLayouts = (
  widgets: WidgetConfig[],
  baseLayouts: GridLayout[]
): { lg: GridLayout[]; md: GridLayout[]; sm: GridLayout[]; xs: GridLayout[] } => {
  const widgetIds = new Set(widgets.map((w) => w.id));
  
  // Filter base layouts to only include existing widgets
  const filteredBase = filterLayoutsByWidgetIds(baseLayouts, widgetIds);
  
  // Generate medium breakpoint layout (similar structure to large)
  const mdLayout = filteredBase.map((item) => ({
    ...item,
    // Adjust for medium screens if needed
    w: item.w > 6 ? 6 : item.w,
  }));
  
  // Generate small breakpoint layout (stacked vertically)
  const smLayout = widgets.map((widget, index) => ({
    i: widget.id,
    x: 0,
    y: index * 8,
    w: 1,
    h: 8,
  }));
  
  // Extra small breakpoint (same as small for mobile)
  const xsLayout = smLayout;
  
  return {
    lg: filteredBase.map((item) => ({
      ...item,
      minW: minById[item.i]?.minW ?? item.minW,
      minH: minById[item.i]?.minH ?? item.minH,
    })),
    md: mdLayout.map((item) => ({
      ...item,
      minW: minById[item.i]?.minW ?? item.minW,
      minH: minById[item.i]?.minH ?? item.minH,
    })),
    sm: smLayout,
    xs: xsLayout,
  };
};

export function DashboardGrid() {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1200);
  const widthRef = useRef(1200); // Track current width to prevent unnecessary updates
  
  useEffect(() => {
    if (!containerRef.current) return;
    const updateWidth = () => {
      if (containerRef.current) {
        const next = containerRef.current.offsetWidth;
        // Only update if width actually changed to prevent unnecessary re-renders
        if (next > 0 && next !== widthRef.current) {
          widthRef.current = next;
          setWidth(next);
        }
      }
    };
    updateWidth();
    const resizeObserver = new ResizeObserver(updateWidth);
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []); // Empty dependency array - only run once on mount
  const [widgets, setWidgets] = useState<WidgetConfig[]>(() => {
    if (typeof window === "undefined") {
      return initialWidgets;
    }
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (!stored) return initialWidgets;
      const parsed = JSON.parse(stored) as StoredLayoutState;
      if (parsed.version !== STORAGE_VERSION) return initialWidgets;
      if (!parsed.widgets?.length) return initialWidgets;
      return initialWidgets.filter((widget) => parsed.widgets.includes(widget.id));
    } catch {
      return initialWidgets;
    }
  });
  const [pinned, setPinned] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (!stored) return {};
      const parsed = JSON.parse(stored) as StoredLayoutState;
      if (parsed.version !== STORAGE_VERSION) return {};
      return parsed.pinned ?? {};
    } catch {
      return {};
    }
  });
  const [keyboardMode, setKeyboardMode] = useState<{
    id: string;
    mode: "move" | "resize";
  } | null>(null);

  // Initialize layouts state with computed layouts
  const [layouts, setLayouts] = useState(() => {
    if (typeof window === "undefined") {
      return generateResponsiveLayouts(initialWidgets, baseLayout);
    }
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (!stored) return generateResponsiveLayouts(initialWidgets, baseLayout);
      const parsed = JSON.parse(stored) as StoredLayoutState;
      if (parsed.version !== STORAGE_VERSION) {
        return generateResponsiveLayouts(initialWidgets, baseLayout);
      }
      const widgetIds = new Set(
        (parsed.widgets?.length ? parsed.widgets : initialWidgets.map((w) => w.id)) ?? []
      );
      const nextLayouts = parsed.layouts ?? generateResponsiveLayouts(initialWidgets, baseLayout);
      const normalized = {
        lg: normalizeBreakpointLayout(nextLayouts.lg, widgetIds, "lg"),
        md: normalizeBreakpointLayout(nextLayouts.md, widgetIds, "md"),
        sm: normalizeBreakpointLayout(nextLayouts.sm, widgetIds, "sm"),
        xs: normalizeBreakpointLayout(nextLayouts.xs, widgetIds, "xs"),
      };
      return isInvalidLayouts(normalized) ? generateResponsiveLayouts(initialWidgets, baseLayout) : normalized;
    } catch {
      return generateResponsiveLayouts(initialWidgets, baseLayout);
    }
  });

  // Sync layouts when widgets change
  // Use widget IDs instead of the entire widgets array to prevent unnecessary re-renders
  const widgetIds = useMemo(() => widgets.map((w) => w.id).sort().join(","), [widgets]);
  
  useEffect(() => {
    const currentWidgetIds = new Set(widgets.map((w) => w.id));
    setLayouts((prevLayouts) => {
      const updated: BreakpointLayouts = {
        lg: filterLayoutsByWidgetIds(prevLayouts.lg, currentWidgetIds),
        md: filterLayoutsByWidgetIds(prevLayouts.md, currentWidgetIds),
        sm: filterLayoutsByWidgetIds(prevLayouts.sm, currentWidgetIds),
        xs: filterLayoutsByWidgetIds(prevLayouts.xs, currentWidgetIds),
      };
      
      // If layouts were filtered (widgets removed), regenerate from scratch
      const prevWidgetIds = new Set(
        [...prevLayouts.lg, ...prevLayouts.md, ...prevLayouts.sm, ...prevLayouts.xs].map((l) => l.i)
      );
      const widgetsChanged = prevWidgetIds.size !== currentWidgetIds.size || 
        [...prevWidgetIds].some((id) => !currentWidgetIds.has(id));
      
      if (widgetsChanged) {
        return generateResponsiveLayouts(widgets, baseLayout);
      }
      
      return updated;
    });
  }, [widgetIds, widgets]); // Use widgetIds string for comparison, widgets for generation

  // Debounce localStorage saves to prevent excessive writes
  useEffect(() => {
    if (typeof window === "undefined") return;
    const timeoutId = setTimeout(() => {
      const payload: StoredLayoutState = {
        version: STORAGE_VERSION,
        layouts,
        widgets: widgets.map((widget) => widget.id),
        pinned,
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    }, 300); // Debounce by 300ms
    
    return () => clearTimeout(timeoutId);
  }, [layouts, widgetIds, pinned]); // Use widgetIds instead of widgets array

  const widgetLookup = useMemo(() => {
    return widgets.reduce<Record<string, WidgetConfig>>((acc, widget) => {
      acc[widget.id] = widget;
      return acc;
    }, {});
  }, [widgets]);

  const togglePin = useCallback((id: string) => {
    setPinned((prev) => ({ ...prev, [id]: !prev[id] }));
    setLayouts((prev) => {
      const updated = { ...prev };
      (Object.keys(updated) as Array<keyof typeof updated>).forEach(
        (breakpoint) => {
          updated[breakpoint] = updated[breakpoint].map((item) =>
            item.i === id ? { ...item, static: !item.static } : item
          );
        }
      );
      return updated;
    });
  }, []);

  // Keyboard navigation handlers
  const handleKeyboardToggle = useCallback((id: string, mode: "move" | "resize") => {
    setKeyboardMode((prev) =>
      prev && prev.id === id && prev.mode === mode ? null : { id, mode }
    );
  }, []);

  const handleKeyboardAction = useCallback(
    (id: string, mode: "move" | "resize", event: React.KeyboardEvent) => {
      if (!keyboardMode || keyboardMode.id !== id || keyboardMode.mode !== mode) {
        if (event.key === "Escape") {
          setKeyboardMode(null);
        }
        return;
      }

      if (event.key === "Escape") {
        setKeyboardMode(null);
        return;
      }

      const step = event.shiftKey ? 2 : 1;
      const keyMap: Record<string, [number, number]> = {
        ArrowUp: [0, -step],
        ArrowDown: [0, step],
        ArrowLeft: [-step, 0],
        ArrowRight: [step, 0],
      };

      if (!keyMap[event.key]) {
        return;
      }

      event.preventDefault();
      const [dx, dy] = keyMap[event.key];

      setLayouts((prev) => {
        const updated = { ...prev };
        (Object.keys(updated) as Array<keyof typeof updated>).forEach(
          (breakpoint) => {
            const cols = colsByBreakpoint[breakpoint] ?? 12;
            updated[breakpoint] = updated[breakpoint].map((item) => {
              if (item.i !== id) return item;

              if (mode === "move") {
                const nextX = Math.max(0, Math.min(item.x + dx, cols - item.w));
                const nextY = Math.max(0, item.y + dy);
                return { ...item, x: nextX, y: nextY };
              }

              const nextW = Math.max(1, Math.min(item.w + dx, cols - item.x));
              const nextH = Math.max(2, item.h + dy);
              return { ...item, w: nextW, h: nextH };
            });
          }
        );
        return updated;
      });
    },
    [keyboardMode]
  );

  // Function to remove a widget (ensures layout sync)
  const removeWidget = useCallback((widgetId: string) => {
    setWidgets((prev) => prev.filter((widget) => widget.id !== widgetId));
    // Layouts will be automatically updated via useEffect
    // Also clean up pinned state
    setPinned((prev) => {
      const updated = { ...prev };
      delete updated[widgetId];
      return updated;
    });
  }, []);

  // Handle layout changes from react-grid-layout
  // Use a ref to track if we're currently updating to prevent loops
  const isUpdatingLayout = useRef(false);
  const lastLayoutUpdateRef = useRef<string>("");
  
  const handleLayoutChange = useCallback(
    (
      currentLayout: Layout,
      allLayouts: Partial<Record<"sm" | "md" | "lg" | "xs", Layout>>
    ) => {
      // Prevent recursive updates
      if (isUpdatingLayout.current) return;
      
      if (allLayouts && typeof allLayouts === "object") {
        const widgetIdsSet = new Set(widgets.map((w) => w.id));
        const current = Array.isArray(currentLayout) ? currentLayout : [];
        const normalized = {
          lg: normalizeBreakpointLayout((allLayouts.lg as unknown as GridLayout[]) ?? (current as unknown as GridLayout[]), widgetIdsSet, "lg"),
          md: normalizeBreakpointLayout((allLayouts.md as unknown as GridLayout[]) ?? (current as unknown as GridLayout[]), widgetIdsSet, "md"),
          sm: normalizeBreakpointLayout((allLayouts.sm as unknown as GridLayout[]) ?? (current as unknown as GridLayout[]), widgetIdsSet, "sm"),
          xs: normalizeBreakpointLayout((allLayouts.xs as unknown as GridLayout[]) ?? (current as unknown as GridLayout[]), widgetIdsSet, "xs"),
        };
        const nextLayouts = isInvalidLayouts(normalized) ? generateResponsiveLayouts(widgets, baseLayout) : normalized;
        
        // Create a hash of the layouts to check if they actually changed
        const layoutHash = JSON.stringify(nextLayouts);
        if (layoutHash === lastLayoutUpdateRef.current) {
          return; // No actual change, skip update
        }
        
        lastLayoutUpdateRef.current = layoutHash;
        isUpdatingLayout.current = true;
        setLayouts(nextLayouts);
        
        // Reset flag after state update completes
        requestAnimationFrame(() => {
          isUpdatingLayout.current = false;
        });
      }
    },
    [widgets]
  );

  const resetLayout = useCallback(() => {
    setWidgets(initialWidgets);
    setPinned({});
    setKeyboardMode(null);
    const nextLayouts = generateResponsiveLayouts(initialWidgets, baseLayout);
    setLayouts(nextLayouts);
    if (typeof window !== "undefined") {
      const payload: StoredLayoutState = {
        version: STORAGE_VERSION,
        layouts: nextLayouts,
        widgets: initialWidgets.map((widget) => widget.id),
        pinned: {},
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    }
  }, []);

  return (
    <div ref={containerRef} className="w-full min-w-0">
      <div className="mb-4 flex flex-wrap items-center justify-end gap-2">
        <Button variant="ghost" size="sm" type="button" onClick={resetLayout}>
          {t("dashboard.resetLayout")}
        </Button>
      </div>
      <ResponsiveGridLayout
        width={width || 1200}
        className="layout w-full"
        layouts={layouts}
        onLayoutChange={handleLayoutChange}
        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
        cols={colsByBreakpoint}
        rowHeight={24}
        margin={[16, 16]}
      >
        {widgets.map((widget) => (
          <div key={widget.id} className="flex">
            <div className="flex h-full w-full flex-col">
              <WidgetShell
                title={t(widget.titleKey)}
                subtitle={t(widget.subtitleKey)}
                pinned={Boolean(pinned[widget.id])}
                onTogglePin={() => togglePin(widget.id)}
                onRemove={() => removeWidget(widget.id)}
                keyboardMode={
                  keyboardMode?.id === widget.id ? keyboardMode.mode : null
                }
                onToggleKeyboardMode={(mode) =>
                  handleKeyboardToggle(widget.id, mode)
                }
                onKeyboardAction={(mode, event) =>
                  handleKeyboardAction(widget.id, mode, event)
                }
              >
                {widgetLookup[widget.id]?.content}
              </WidgetShell>
            </div>
          </div>
        ))}
      </ResponsiveGridLayout>
    </div>
  );
}

// Export type for external use
export type { WidgetConfig };
