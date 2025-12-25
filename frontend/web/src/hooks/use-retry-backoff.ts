import { useCallback, useRef } from "react";

export function useRetryWithBackoff(params?: {
  initialMs?: number;
  maxMs?: number;
  factor?: number;
}) {
  const initialMs = params?.initialMs ?? 500;
  const maxMs = params?.maxMs ?? 8000;
  const factor = params?.factor ?? 2;
  const attemptRef = useRef(0);

  const reset = useCallback(() => {
    attemptRef.current = 0;
  }, []);

  const nextDelay = useCallback(() => {
    const attempt = attemptRef.current;
    attemptRef.current += 1;
    const delay = Math.min(maxMs, initialMs * Math.pow(factor, attempt));
    // jitter
    const jitter = delay * (0.2 * Math.random());
    return delay + jitter;
  }, [factor, initialMs, maxMs]);

  return { nextDelay, reset };
}

