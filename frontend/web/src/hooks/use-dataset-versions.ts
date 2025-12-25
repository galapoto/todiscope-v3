import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export function useDatasetVersions() {
  return useQuery({
    queryKey: ["dataset-versions"],
    queryFn: () => api.getDatasetVersions(),
    staleTime: 5 * 60 * 1000,
    retry: false,
    select: (versions) =>
      versions
        .slice()
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ),
  });
}
