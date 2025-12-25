# Widget System Architecture (TodiScope v3 Frontend)

## Directory Structure

```
frontend/
  src/
    components/
      WidgetContainer.tsx
      Widget.tsx
      WidgetManager.tsx
      widgets/
        FinancialExposureWidget.tsx
        PendingReviewsWidget.tsx
        CO2EmissionsWidget.tsx
        AIInsightsWidget.tsx
      Modal.tsx
      Chart.tsx
      Table.tsx
    hooks/
      useWidgetState.ts
      useRealTimeData.ts
      useWebSocket.ts
      useModal.ts
    context/
      WidgetContext.tsx
    utils/
      dragDropUtils.ts
      resizeUtils.ts
      accessibility.ts
    tests/
      WidgetContainer.test.tsx
      Widget.test.tsx
      Modal.test.tsx
      useRealTimeData.test.ts
      ...
  public/
    index.html
  package.json
  ...
```

## Key Components

- **WidgetContainer**: Layout, drag-and-drop, resizing, add/remove widgets.
- **Widget**: Base widget, receives type, data, size, position.
- **WidgetManager**: Handles widget state, persistence (localStorage/Context), add/remove logic.
- **Predefined Widgets**: FinancialExposureWidget, PendingReviewsWidget, CO2EmissionsWidget, AIInsightsWidget.
- **Modal**: For details/confirmation, with focus trap and aria.
- **Chart/Table**: Data visualizations (Recharts), dynamic updates.
- **Hooks**: useWidgetState (persistent state), useRealTimeData (React Query polling + WebSocket/SSE), useModal.
- **Accessibility**: Focus management, aria-live, keyboard navigation.
- **Tests**: Unit tests for all interactive components and hooks.

## Data Flow

- Widget state is managed in WidgetManager/WidgetContext and persisted to localStorage.
- Real-time data is fetched via React Query (polling) and updated via WebSocket/SSE.
- Widgets subscribe to data and update dynamically.
- Modals are managed via useModal and are fully accessible.

## Next Steps

1. Scaffold WidgetContainer, Widget, WidgetManager, and WidgetContext.
2. Implement drag-and-drop and resizing (accessible).
3. Add persistent state logic (localStorage + Context).
4. Implement predefined widgets and AI-powered widget placeholder.
5. Set up React Query hooks and WebSocket/SSE for real-time data.
6. Build Modal system with accessibility.
7. Add charts/tables with Recharts.
8. Write unit tests for all components and hooks.
