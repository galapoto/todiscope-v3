"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type OnboardingState = {
  active: boolean;
  step: number;
  completed: boolean;
  seen: boolean;
};

type OnboardingContextValue = OnboardingState & {
  start: () => void;
  skip: () => void;
  resume: () => void;
  next: () => void;
  back: () => void;
  close: () => void;
};

const OnboardingContext = createContext<OnboardingContextValue | undefined>(undefined);
const storageKey = "todiscope.onboarding";

function loadState(): OnboardingState {
  if (typeof window === "undefined") {
    return { active: false, step: 0, completed: false, seen: false };
  }
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return { active: false, step: 0, completed: false, seen: false };
    const parsed = JSON.parse(raw) as OnboardingState;
    return {
      active: Boolean(parsed.active),
      step: Number(parsed.step ?? 0),
      completed: Boolean(parsed.completed),
      seen: Boolean(parsed.seen),
    };
  } catch {
    return { active: false, step: 0, completed: false, seen: false };
  }
}

function persist(state: OnboardingState) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey, JSON.stringify(state));
}

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<OnboardingState>({
    active: false,
    step: 0,
    completed: false,
    seen: false,
  });

  useEffect(() => {
    setState(loadState());
  }, []);

  const value = useMemo<OnboardingContextValue>(() => {
    return {
      ...state,
      start: () => {
        const next = { active: true, step: 0, completed: false, seen: true };
        setState(next);
        persist(next);
      },
      skip: () => {
        const next = { active: false, step: 0, completed: true, seen: true };
        setState(next);
        persist(next);
      },
      resume: () => {
        const next = { ...state, active: true, seen: true };
        setState(next);
        persist(next);
      },
      next: () => {
        const nextState = { ...state, step: state.step + 1 };
        setState(nextState);
        persist(nextState);
      },
      back: () => {
        const nextState = { ...state, step: Math.max(0, state.step - 1) };
        setState(nextState);
        persist(nextState);
      },
      close: () => {
        const next = { ...state, active: false, seen: true };
        setState(next);
        persist(next);
      },
    };
  }, [state]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error("useOnboarding must be used within OnboardingProvider");
  }
  return context;
}
