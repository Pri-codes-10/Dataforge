/**
 * Application Configuration
 *
 * Centralizes environment variables and application-wide settings.
 * All access to import.meta.env should go through this file to ensure
 * clean separation and easy testing/mocking.
 */

export const config = {
  /**
   * Base URL for the future SUTRA backend API.
   * Defined in .env via VITE_API_URL.
   * Default: empty string (local relative requests / mock fallback).
   */
  apiUrl: (import.meta.env["VITE_API_URL"] as string | undefined) ?? "",

  /**
   * Application display name.
   */
  appName: "SUTRA",

  /**
   * Application tag line.
   */
  tagline: "The conversation never loses the thread.",

  /**
   * Environment mode.
   */
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;

export type AppConfig = typeof config;
