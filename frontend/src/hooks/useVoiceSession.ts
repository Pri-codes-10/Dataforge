/**
 * useVoiceSession Hook
 *
 * Manages frontend voice session state, orb animation status,
 * and controls for starting/stopping/interrupting sessions.
 * Consumes `voiceService` exclusively.
 */

import { useState, useCallback } from "react";
import type { VoiceState } from "@/types";
import {
  demoVoiceStates,
  getVoiceStateLabel,
  isVoiceStateActive,
  startVoiceSession,
  stopVoiceSession,
  sendInterruption,
} from "@/services/voiceService";

export { demoVoiceStates };

export function useVoiceSession(initialState: VoiceState = "IDLE") {
  const [voiceState, setVoiceState] = useState<VoiceState>(initialState);

  const label = getVoiceStateLabel(voiceState);
  const isActive = isVoiceStateActive(voiceState);

  const cycleNextState = useCallback(() => {
    setVoiceState((current) => {
      const currentIndex = demoVoiceStates.indexOf(current);
      const nextIndex = (currentIndex + 1) % demoVoiceStates.length;
      return demoVoiceStates[nextIndex] ?? "IDLE";
    });
  }, []);

  const setState = useCallback((state: VoiceState) => {
    setVoiceState(state);
  }, []);

  const start = useCallback(async () => {
    await startVoiceSession();
    setVoiceState("LISTENING");
  }, []);

  const stop = useCallback(async () => {
    await stopVoiceSession();
    setVoiceState("IDLE");
  }, []);

  const interrupt = useCallback(async () => {
    await sendInterruption();
    setVoiceState("USER_INTERRUPTED");
  }, []);

  return {
    voiceState,
    label,
    isActive,
    setState,
    cycleNextState,
    start,
    stop,
    interrupt,
  };
}
