"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ThemeMode = "dark" | "light";

type ThemeContextValue = {
  mode: ThemeMode;
  toggle: () => void;
  setMode: (mode: ThemeMode) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "todiscope-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("dark");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
    const initial = stored ?? "dark";
    setModeState(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const setMode = useCallback((nextMode: ThemeMode) => {
    setModeState(nextMode);
    document.documentElement.setAttribute("data-theme", nextMode);
    window.localStorage.setItem(STORAGE_KEY, nextMode);
  }, []);

  const toggle = useCallback(() => {
    setMode(mode === "dark" ? "light" : "dark");
  }, [mode, setMode]);

  const value = useMemo(() => ({ mode, toggle, setMode }), [mode, toggle, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
