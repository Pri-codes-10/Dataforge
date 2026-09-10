/**
 * useVoiceSession Hook
 *
 * Manages frontend voice session state, hands-free continuous microphone capture,
 * backend WebSocket events, audio playback, and error reporting.
 */

import { useState, useEffect, useCallback } from "react";
import type { VoiceState } from "@/types";
import {
  demoVoiceStates,
  getVoiceStateLabel,
  isVoiceStateActive,
  voiceManager,
  startVoiceSession,
  stopVoiceSession,
  sendInterruption,
} from "@/services/voiceService";

export { demoVoiceStates };

export function useVoiceSession(initialState: VoiceState = "IDLE") {
  const [voiceState, setVoiceState] = useState<VoiceState>(() => voiceManager.getState() || initialState);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastTranscript, setLastTranscript] = useState<string>("");
  const [lastResponse, setLastResponse] = useState<string>("");
  const [permissionDenied, setPermissionDenied] = useState<boolean>(false);
  const [isSessionActive, setIsSessionActive] = useState<boolean>(() => voiceManager.isConversationActive);

  useEffect(() => {
    const unsubscribe = voiceManager.subscribe({
      onStateChange: (newState) => {
        setVoiceState(newState);
        setIsSessionActive(voiceManager.isConversationActive);
        if (newState !== "ERROR") {
          setErrorMessage(null);
        }
      },
      onTranscript: (text) => {
        setLastTranscript(text);
      },
      onResponse: (text) => {
        setLastResponse(text);
      },
      onError: (msg) => {
        setErrorMessage(msg);
        if (msg.includes("access is required") || msg.includes("permission")) {
          setPermissionDenied(true);
        }
      },
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const label = getVoiceStateLabel(voiceState);
  const isActive = isVoiceStateActive(voiceState);
  const isRecording = voiceState === "RECORDING";

  const cycleNextState = useCallback(() => {
    setVoiceState((current) => {
      const currentIndex = demoVoiceStates.indexOf(current);
      const nextIndex = (currentIndex + 1) % demoVoiceStates.length;
      const next = demoVoiceStates[nextIndex] ?? "IDLE";
      return next;
    });
  }, []);

  const setState = useCallback((state: VoiceState) => {
    setVoiceState(state);
  }, []);

  const start = useCallback(async () => {
    try {
      setPermissionDenied(false);
      setErrorMessage(null);
      await startVoiceSession();
      setIsSessionActive(true);
    } catch (err: any) {
      if (err?.message?.includes("access is required")) {
        setPermissionDenied(true);
      }
    }
  }, []);

  const stop = useCallback(async () => {
    await stopVoiceSession();
    setIsSessionActive(false);
  }, []);

  const toggleRecording = useCallback(async () => {
    if (voiceManager.isConversationActive) {
      await stopVoiceSession();
      setIsSessionActive(false);
    } else {
      try {
        setPermissionDenied(false);
        setErrorMessage(null);
        await startVoiceSession();
        setIsSessionActive(true);
      } catch (err: any) {
        if (err?.message?.includes("access is required")) {
          setPermissionDenied(true);
        }
      }
    }
  }, []);

  const interrupt = useCallback(async () => {
    await sendInterruption();
  }, []);

  return {
    voiceState,
    label,
    isActive,
    isRecording,
    isSessionActive,
    errorMessage,
    permissionDenied,
    lastTranscript,
    lastResponse,
    setState,
    cycleNextState,
    start,
    stop,
    toggleRecording,
    startConversation: start,
    endConversation: stop,
    interrupt,
  };
}
