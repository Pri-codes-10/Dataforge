/**
 * Language Service
 *
 * Manages language detection state. Currently returns mock data.
 * When the backend is ready, language detection results will be pushed from
 * the SUTRA voice pipeline as part of the conversation state stream.
 */

import type { LanguageDetection } from "@/types";
import { mockLanguageDetection } from "@/data/mockDashboard";

/**
 * Returns the current language detection state.
 * Future: This will be pushed from the backend via WebSocket/SSE
 * as part of the conversation state update stream.
 */
export async function getLanguageDetection(): Promise<LanguageDetection> {
  // TODO: Replace with real-time data from the backend state stream
  return Promise.resolve(mockLanguageDetection);
}

/**
 * Formats a list of detected language names into a combined label.
 * e.g. ["Hindi", "English"] → "Hindi + English"
 */
export function formatLanguageLabel(languages: string[]): string {
  return languages.join(" + ");
}

/**
 * Returns true if the user is code-switching (mixing multiple languages).
 */
export function isCodeSwitching(languages: string[]): boolean {
  return languages.length > 1;
}
