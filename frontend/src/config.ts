/**
 * Application Configuration
 *
 * Centralizes environment variables and application-wide settings.
 * Backend connects to port 8000 by default (or VITE_API_URL if set).
 */

const rawApiUrl = (import.meta.env["VITE_API_URL"] as string | undefined) || "http://localhost:8000";
// Clean trailing slashes
const normalizedApiUrl = rawApiUrl.replace(/\/+$/, "");

export const config = {
  /**
   * Base URL for the SUTRA backend API.
   * Default: http://localhost:8000
   */
  apiUrl: normalizedApiUrl,

  /**
   * Realtime WebSocket URL for voice and state synchronization.
   * Default: ws://localhost:8000/ws/voice
   */
  wsUrl: `${normalizedApiUrl.replace(/^http/, "ws")}/ws/voice`,

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
