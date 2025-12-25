"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider } from "@/components/theme/theme-context";
import { initializeI18n } from "@/lib/i18n";
import { DatasetProvider } from "@/components/data/dataset-context";
import { AuthProvider } from "@/components/auth/auth-context";
import { SearchProvider } from "@/components/search/search-context";
import { OnboardingProvider } from "@/components/onboarding/onboarding-context";
import { realtime } from "@/lib/realtime-manager";
import { ErrorBoundary } from "@/components/system/error-boundary";
import { EngineResultsProvider } from "@/components/engines/engine-results-context";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  initializeI18n();

  // Centralize realtime + React Query integration.
  realtime.attachQueryClient(queryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AuthProvider>
          <ThemeProvider>
            <DatasetProvider>
              <SearchProvider>
                <EngineResultsProvider>
                  <OnboardingProvider>{children}</OnboardingProvider>
                </EngineResultsProvider>
              </SearchProvider>
            </DatasetProvider>
          </ThemeProvider>
        </AuthProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
