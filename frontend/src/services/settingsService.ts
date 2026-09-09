/**
 * Settings Service
 *
 * Manages application settings. Currently backed by localStorage with typed defaults.
 * When the backend is ready, settings will sync with the user's profile on the server:
 * e.g. GET /settings, PATCH /settings
 */

import type { AppSettings } from "@/types";

const SETTINGS_STORAGE_KEY = "sutra-app-settings";

export const defaultSettings: AppSettings = {
  voice: {
    engine: "rime",
    speed: 1.0,
    pitch: 1.0,
    accent: "aria",
  },
  language: {
    primary: "Hindi",
    secondary: "English",
    autoDetectCodeSwitching: true,
  },
  conversation: {
    retainContextTurns: 10,
    staleResultProtection: true,
    interruptible: true,
  },
  taskExecution: {
    maxTimeoutSeconds: 30,
    notifyOnCompletion: true,
  },
  appearance: {
    theme: "light",
    reducedMotion: false,
  },
};

/**
 * Returns the current application settings.
 * Reads from localStorage if available, falling back to defaultSettings.
 * Future: GET /settings
 */
export async function getSettings(): Promise<AppSettings> {
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        return Promise.resolve({ ...defaultSettings, ...JSON.parse(stored) });
      }
    } catch {
      // Fall through to defaults if parsing fails
    }
  }
  return Promise.resolve(defaultSettings);
}

/**
 * Updates application settings partially or fully.
 * Saves to localStorage.
 * Future: PATCH /settings
 */
export async function updateSettings(partial: Partial<AppSettings>): Promise<AppSettings> {
  const current = await getSettings();
  const updated: AppSettings = {
    ...current,
    ...partial,
    voice: { ...current.voice, ...partial.voice },
    language: { ...current.language, ...partial.language },
    conversation: { ...current.conversation, ...partial.conversation },
    taskExecution: { ...current.taskExecution, ...partial.taskExecution },
    appearance: { ...current.appearance, ...partial.appearance },
  };

  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Storage unavailable or quota exceeded
    }
  }

  return Promise.resolve(updated);
}
