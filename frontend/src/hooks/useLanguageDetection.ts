/**
 * useLanguageDetection Hook
 *
 * Custom React hook for accessing language detection state.
 * Subscribes to live language detection events from the backend WebSocket,
 * with fallback to languageService.
 */

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLanguageDetection } from "@/services/languageService";
import { voiceManager } from "@/services/voiceService";
import type { LanguageDetection } from "@/types";

export const LANGUAGE_DETECTION_QUERY_KEY = ["languageDetection"] as const;

export function useLanguageDetection() {
  const query = useQuery<LanguageDetection, Error>({
    queryKey: LANGUAGE_DETECTION_QUERY_KEY,
    queryFn: getLanguageDetection,
  });

  const [liveLang, setLiveLang] = useState<{
    languages: string[];
    codeSwitched: boolean;
    label: string;
  } | null>(null);

  useEffect(() => {
    const unsubscribe = voiceManager.subscribe({
      onLanguage: (lang: string, codeSwitched: boolean) => {
        let languages = ["English"];
        let label = "English";

        if (lang === "hi") {
          languages = ["Hindi"];
          label = "Hindi";
        } else if (lang === "mixed" || codeSwitched) {
          languages = ["Hindi", "English"];
          label = "Hindi + English";
        } else if (lang === "bn") {
          languages = ["Bengali"];
          label = "Bengali";
        }

        setLiveLang({
          languages,
          codeSwitched,
          label,
        });
      },
    });

    return () => unsubscribe();
  }, []);

  const data = query.data;
  const activeLanguages = liveLang?.languages ?? data?.activeLanguages ?? ["Hindi", "English"];
  const codeSwitched = liveLang?.codeSwitched ?? data?.codeSwitched ?? true;
  const label = liveLang?.label ?? data?.label ?? "Hindi + English";

  return {
    languageDetection: data,
    activeLanguages,
    detectedLanguages: activeLanguages,
    codeSwitched,
    label,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
