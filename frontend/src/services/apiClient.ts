/**
 * SUTRA API Client
 *
 * A thin fetch wrapper configured to use config.apiUrl (from VITE_API_URL) as the backend base URL.
 *
 * CURRENT STATE: No backend exists yet. This client is prepared but not called
 * by default. Services serve from isolated mock data.
 *
 * FUTURE USE: When the backend is available, set VITE_API_URL in your .env
 * file and the services in `src/services/` will route through this client.
 *
 * Usage:
 *   import { apiClient } from "@/services/apiClient";
 *   const data = await apiClient.get<Conversation[]>("/conversations");
 */

import { config } from "@/config";
import type { AppError } from "@/types";

const BASE_URL = config.apiUrl;

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  try {
    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });

    if (!response.ok) {
      const error: AppError = {
        type: "NETWORK_ERROR",
        message: `API error ${response.status} ${response.statusText} — ${method} ${path}`,
        code: response.status,
      };
      throw error;
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if ((err as AppError).type) {
      throw err;
    }
    const appError: AppError = {
      type: "NETWORK_ERROR",
      message: err instanceof Error ? err.message : "Network request failed",
      details: err,
    };
    throw appError;
  }
}

export const apiClient = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  getBaseUrl: () => BASE_URL,
};
