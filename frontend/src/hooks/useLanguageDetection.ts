/**
 * useLanguageDetection Hook
 *
 * Custom React hook for accessing language detection state.
 * Subscribes to live language detection events from the backend WebSocket.
 */

import { useState, useEffect } from "react";
import { voiceManager } from "@/services/voiceService";
import type { LanguageDetection } from "@/types";

export function useLanguageDetection() {
  const [liveLang, setLiveLang] = useState<{
    languages: string[];
    codeSwitched: boolean;
    label: string;
  }>({
    languages: ["English"],
    codeSwitched: false,
    label: "English",
  });

  useEffect(() => {
    const unsubscribe = voiceManager.subscribe({
      onLanguage: (lang: string, codeSwitched: boolean, languages?: string[], label?: string) => {
        let finalLanguages = languages;
        let finalLabel = label;

        if (!finalLanguages || finalLanguages.length === 0) {
          if (lang === "hi") {
            finalLanguages = ["Hindi"];
            finalLabel = "Hindi";
          } else if (lang === "bn") {
            finalLanguages = ["Bengali"];
            finalLabel = "Bengali";
          } else if (lang === "mixed" || codeSwitched) {
            finalLanguages = ["Hindi", "English"];
            finalLabel = "Hindi + English";
          } else {
            finalLanguages = ["English"];
            finalLabel = "English";
          }
        }

        setLiveLang({
          languages: finalLanguages,
          codeSwitched: codeSwitched,
          label: finalLabel || finalLanguages.join(" + "),
        });
      },
      onConversationState: (state) => {
        if (state.language && state.language.length > 0) {
          const l = state.language[0].toLowerCase();
          const isCs = state.codeSwitched ?? false;
          let langs = ["English"];
          let lbl = "English";
          if (l === "hi" || l === "hindi") {
            langs = isCs ? ["Hindi", "English"] : ["Hindi"];
            lbl = isCs ? "Hindi + English" : "Hindi";
          } else if (l === "bn" || l === "bengali") {
            langs = isCs ? ["Bengali", "English"] : ["Bengali"];
            lbl = isCs ? "Bengali + English" : "Bengali";
          }
          setLiveLang({
            languages: langs,
            codeSwitched: isCs,
            label: lbl,
          });
        }
      },
    });

    return () => unsubscribe();
  }, []);

  const languageDetection: LanguageDetection = {
    detectedLanguages: liveLang.languages,
    activeLanguages: liveLang.languages,
    codeSwitched: liveLang.codeSwitched,
    label: liveLang.label,
  };

  return {
    languageDetection,
    activeLanguages: liveLang.languages,
    detectedLanguages: liveLang.languages,
    codeSwitched: liveLang.codeSwitched,
    label: liveLang.label,
    isLoading: false,
    isError: false,
    error: null,
  };
}
