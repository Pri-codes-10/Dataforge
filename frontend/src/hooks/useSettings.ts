/**
 * useSettings Hook
 *
 * Custom React hook for managing application configuration.
 * Consumes `settingsService` exclusively.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSettings, updateSettings as updateSettingsService, defaultSettings } from "@/services/settingsService";
import type { AppSettings } from "@/types";

export const SETTINGS_QUERY_KEY = ["settings"] as const;

export function useSettings() {
  const queryClient = useQueryClient();

  const query = useQuery<AppSettings, Error>({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: getSettings,
    staleTime: Infinity,
  });

  const updateMutation = useMutation({
    mutationFn: (partial: Partial<AppSettings>) => updateSettingsService(partial),
    onSuccess: (newSettings) => {
      queryClient.setQueryData(SETTINGS_QUERY_KEY, newSettings);
    },
  });

  return {
    settings: query.data ?? defaultSettings,
    isLoading: query.isLoading,
    updateSettings: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  };
}
