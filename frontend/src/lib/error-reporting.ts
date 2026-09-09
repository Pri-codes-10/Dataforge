/**
 * Generic frontend error reporter.
 *
 * Currently logs errors to the console. This is intentionally a no-op in
 * the browser beyond console output — no third-party telemetry is wired up.
 *
 * When a real error tracking service (e.g. Sentry) is added, replace the
 * body of `reportError` with the appropriate SDK call.
 */

type ErrorContext = Record<string, unknown>;

export function reportError(error: unknown, context: ErrorContext = {}): void {
  if (typeof console !== "undefined") {
    console.error("[SUTRA] Unhandled error", error, context);
  }
}
