/**
 * useLanguageDetection Hook
 *
 * Custom React hook for accessing language detection state.
 * Consumes `languageService` exclusively.
 */

import { useQuery } from "@tanstack/react-query";
import { getLanguageDetection } from "@/services/languageService";
import type { LanguageDetection } from "@/types";

export const LANGUAGE_DETECTION_QUERY_KEY = ["languageDetection"] as const;

export function useLanguageDetection() {
  const query = useQuery<LanguageDetection, Error>({
    queryKey: LANGUAGE_DETECTION_QUERY_KEY,
    queryFn: getLanguageDetection,
  });

  const data = query.data;

  return {
    languageDetection: data,
    activeLanguages: data?.activeLanguages ?? ["Hindi", "English"],
    detectedLanguages: data?.detectedLanguages ?? ["Hindi", "English"],
    codeSwitched: data?.codeSwitched ?? true,
    label: data?.label ?? "Hindi + English",
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
