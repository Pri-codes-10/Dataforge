/**
 * Voice Service
 *
 * Manages voice session state. Currently a local state-only implementation.
 * When the backend is ready, this service will connect to the SUTRA voice
 * pipeline (STT → LLM → Tools → Rime) via WebSocket or Server-Sent Events.
 *
 * NOTE: Do not implement STT or Rime here — those are backend concerns.
 * This service only manages the frontend state of the voice session.
 */

import type { VoiceState } from "@/types";

/**
 * The ordered demo states for the voice orb state-cycle button on the dashboard.
 * In a live connected environment, these will be pushed as session events.
 */
export const demoVoiceStates: VoiceState[] = [
  "IDLE",
  "LISTENING",
  "TRANSCRIBING",
  "THINKING",
  "TOOL_RUNNING",
  "SPEAKING",
];

/**
 * Returns the human-readable label for a given VoiceState.
 * Used by the voice orb UI and microphone button.
 */
export function getVoiceStateLabel(state: VoiceState): string {
  const labels: Record<VoiceState, string> = {
    IDLE: "Tap to speak",
    LISTENING: "Listening...",
    TRANSCRIBING: "Transcribing...",
    THINKING: "Thinking...",
    TOOL_RUNNING: "Working...",
    USER_INTERRUPTED: "Interrupted",
    TASK_UPDATED: "Task updated",
    SPEAKING: "Speaking...",
    CANCELLED: "Cancelled",
    ERROR: "Error",
    STALE_RESULT_REJECTED: "Retrying...",
  };
  return labels[state] ?? state;
}

/**
 * Returns whether the voice orb should animate for a given state.
 */
export function isVoiceStateActive(state: VoiceState): boolean {
  return state !== "IDLE" && state !== "CANCELLED" && state !== "ERROR";
}

/**
 * Starts a voice session.
 * Future: Initiates WebSocket connection to VITE_API_URL/voice/session
 */
export async function startVoiceSession(): Promise<void> {
  // TODO: Connect to backend voice WebSocket
  console.info("[voiceService] startVoiceSession — mock handled");
  return Promise.resolve();
}

/**
 * Stops the current voice session.
 * Future: Closes the WebSocket connection gracefully
 */
export async function stopVoiceSession(): Promise<void> {
  // TODO: Disconnect from backend voice WebSocket
  console.info("[voiceService] stopVoiceSession — mock handled");
  return Promise.resolve();
}

/**
 * Sends an interruption signal to the backend (user spoke while agent was speaking).
 * Future: POST /voice/session/:id/interrupt
 */
export async function sendInterruption(): Promise<void> {
  // TODO: apiClient.post("/voice/session/current/interrupt", {});
  console.info("[voiceService] sendInterruption — mock handled");
  return Promise.resolve();
}
