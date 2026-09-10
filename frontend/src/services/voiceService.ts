/**
 * Voice Service
 *
 * Manages browser microphone capture (16kHz WAV), hands-free Voice Activity
 * Detection (VAD), barge-in interruption, continuous conversation lifecycle,
 * realtime WebSocket connection to the SUTRA backend, Rime audio playback,
 * and dynamic task pipeline updates.
 */

import { config } from "@/config";
import type {
  VoiceState,
  TaskPipelineStep,
  ActiveToolExecution,
  ConversationState,
} from "@/types";

export const demoVoiceStates: VoiceState[] = [
  "IDLE",
  "LISTENING",
  "RECORDING",
  "TRANSCRIBING",
  "THINKING",
  "TOOL_RUNNING",
  "SPEAKING",
];

export function getVoiceStateLabel(state: VoiceState): string {
  const labels: Record<VoiceState, string> = {
    IDLE: "Tap to start conversation",
    LISTENING: "Listening...",
    RECORDING: "Listening to you...",
    TRANSCRIBING: "Understanding...",
    THINKING: "Thinking...",
    TOOL_RUNNING: "Checking...",
    USER_INTERRUPTED: "Interrupted",
    TASK_UPDATED: "Task updated",
    SPEAKING: "SUTRA is speaking...",
    CANCELLED: "Cancelled",
    ERROR: "Error occurred",
    STALE_RESULT_REJECTED: "Stale request superseded",
  };
  return labels[state] ?? state;
}

export function isVoiceStateActive(state: VoiceState): boolean {
  return state !== "IDLE" && state !== "CANCELLED" && state !== "ERROR";
}

export interface VoiceEventHandlers {
  onStateChange?: (state: VoiceState) => void;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  onResponse?: (text: string) => void;
  onLanguage?: (lang: string, codeSwitched: boolean, languages?: string[], label?: string) => void;
  onPipelineEvent?: (event: {
    event: string;
    label: string;
    status?: string | undefined;
    tool?: string | undefined;
    requestId?: string | undefined;
  }) => void;
  onPipelineSteps?: (steps: TaskPipelineStep[], isRunning: boolean) => void;
  onToolEvent?: (tool: {
    toolName: string;
    requestId: string;
    status: string;
    isCurrent: boolean;
    result?: string;
  }) => void;
  onStaleResult?: (stale: {
    requestId: string;
    isCurrent: boolean;
    message: string;
  }) => void;
  onConversationState?: (state: Partial<ConversationState>) => void;
  onError?: (errorMessage: string) => void;
  onRimeAudioStatus?: (status: "idle" | "speaking" | "completed") => void;
}

interface WsIncomingMessage {
  type?: string;
  text?: string;
  final?: boolean;
  language?: string;
  code_switched?: boolean;
  languages?: string[];
  event?: string;
  label?: string;
  status?: string;
  tool?: string;
  toolName?: string;
  requestId?: string;
  isCurrent?: boolean;
  data?: any;
  format?: string;
  message?: string;
  steps?: TaskPipelineStep[];
  isRunning?: boolean;
  result?: any;
}

// ---------------------------------------------------------------------------
// PCM to 16kHz WAV encoder utility
// ---------------------------------------------------------------------------
function encodeWavPcm16(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([view], { type: "audio/wav" });
}

// ---------------------------------------------------------------------------
// Voice Session Manager (Continuous Conversational Agent)
// ---------------------------------------------------------------------------
class VoiceSessionManager {
  private ws: WebSocket | null = null;
  private audioStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private currentUtteranceChunks: Float32Array[] = [];
  private currentAudio: HTMLAudioElement | null = null;
  private currentAudioUrl: string | null = null;
  private currentState: VoiceState = "IDLE";
  private handlers: Set<VoiceEventHandlers> = new Set();
  private reconnectTimer: number | null = null;
  private watchdogTimer: number | null = null;

  // Continuous Conversation & VAD Parameters
  public isConversationActive = false;
  private silenceDurationMs = 0;
  private speechDurationMs = 0;
  private isUserSpeaking = false;

  // Configurable VAD Thresholds
  public SPEECH_RMS_THRESHOLD = 0.016; // Speech start threshold
  public BARGE_IN_RMS_THRESHOLD = 0.040; // Barge-in interruption threshold
  public SILENCE_TIMEOUT_MS = 800; // Sustained silence to end utterance
  public MIN_SPEECH_DURATION_MS = 280; // Minimum speech to avoid accidental noise

  constructor() {
    if (typeof window !== "undefined") {
      this.connectWebSocket();
    }
  }

  public subscribe(handlers: VoiceEventHandlers): () => void {
    this.handlers.add(handlers);
    return () => {
      this.handlers.delete(handlers);
    };
  }

  public getState(): VoiceState {
    return this.currentState;
  }

  private setState(state: VoiceState) {
    this.currentState = state;
    this.handlers.forEach((h) => h.onStateChange?.(state));
  }

  private clearWatchdog() {
    if (this.watchdogTimer) {
      window.clearTimeout(this.watchdogTimer);
      this.watchdogTimer = null;
    }
  }

  private setWatchdog(timeoutMs = 20000, errorMsg = "Speech processing timed out. Returning to listening.") {
    this.clearWatchdog();
    this.watchdogTimer = window.setTimeout(() => {
      if (this.currentState === "TRANSCRIBING" || this.currentState === "THINKING") {
        console.warn("[VoiceService] Watchdog timeout fired.");
        this.emitError(errorMsg);
        if (this.isConversationActive) {
          this.setState("LISTENING");
        }
      }
    }, timeoutMs);
  }

  private emitError(message: string) {
    this.clearWatchdog();
    this.handlers.forEach((h) => h.onError?.(message));
  }

  public connectWebSocket() {
    if (typeof window === "undefined") return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(config.wsUrl);

      this.ws.onopen = () => {
        console.info("[VoiceService] Connected to SUTRA WebSocket at", config.wsUrl);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleIncomingMessage(message);
        } catch (e) {
          console.warn("[VoiceService] Non-JSON WS message received:", event.data);
        }
      };

      this.ws.onerror = (err) => {
        console.error("[VoiceService] WebSocket error:", err);
      };

      this.ws.onclose = () => {
        console.warn("[VoiceService] WebSocket connection closed. Reconnecting...");
        if (!this.reconnectTimer) {
          this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;
            this.connectWebSocket();
          }, 2000);
        }
      };
    } catch (err) {
      console.error("[VoiceService] Failed to initialize WebSocket:", err);
    }
  }

  private handleIncomingMessage(message: WsIncomingMessage) {
    switch (message.type) {
      case "transcript":
        this.clearWatchdog();
        if (message.text !== undefined) {
          this.handlers.forEach((h) => h.onTranscript?.(message.text!, message.final ?? true));
          if (message.final) {
            this.setState("THINKING");
            this.setWatchdog(25000, "Agent response timed out.");
          }
        }
        break;

      case "language":
        if (message.language !== undefined) {
          this.handlers.forEach((h) =>
            h.onLanguage?.(message.language!, message.code_switched ?? false, message.languages, message.label),
          );
        }
        break;

      case "pipeline":
        if (message.steps) {
          this.handlers.forEach((h) => h.onPipelineSteps?.(message.steps!, message.isRunning ?? false));
        }
        break;

      case "tool_event":
        if (message.event === "TOOL_STARTED") {
          this.setState("TOOL_RUNNING");
          this.handlers.forEach((h) =>
            h.onToolEvent?.({
              toolName: message.toolName || message.tool || "Search API",
              requestId: message.requestId || "TASK-0001",
              status: "running",
              isCurrent: message.isCurrent ?? true,
            }),
          );
        } else if (message.event === "TOOL_COMPLETED") {
          this.handlers.forEach((h) =>
            h.onToolEvent?.({
              toolName: message.toolName || message.tool || "Search API",
              requestId: message.requestId || "TASK-0001",
              status: "completed",
              isCurrent: message.isCurrent ?? true,
              result: message.result,
            }),
          );
        }
        break;

      case "stale_result":
        if (message.requestId) {
          this.handlers.forEach((h) =>
            h.onStaleResult?.({
              requestId: message.requestId!,
              isCurrent: false,
              message: message.message || "Stale result rejected",
            }),
          );
        }
        break;

      case "pipeline_event":
        if (message.event && message.label) {
          this.handlers.forEach((h) =>
            h.onPipelineEvent?.({
              event: message.event!,
              label: message.label!,
              status: message.status,
              tool: message.tool,
              requestId: message.requestId,
            }),
          );
        }
        if (message.event === "TOOL_STARTED") {
          this.setState("TOOL_RUNNING");
        } else if (message.event === "REQUEST_RECEIVED") {
          this.setState("TRANSCRIBING");
        } else if (message.event === "CANCELLED") {
          this.clearWatchdog();
          this.setState("CANCELLED");
        } else if (message.event === "USER_INTERRUPTED") {
          this.clearWatchdog();
          this.setState("USER_INTERRUPTED");
        }
        break;

      case "response":
        this.clearWatchdog();
        if (message.text !== undefined) {
          this.handlers.forEach((h) => h.onResponse?.(message.text!));
        }
        break;

      case "state":
        if (message.data) {
          this.handlers.forEach((h) => h.onConversationState?.(message.data));
        }
        break;

      case "rime_audio":
        this.clearWatchdog();
        if (message.data) {
          this.playRimeAudio(message.data, message.format ?? "audio/wav");
        }
        break;

      case "status":
        if (message.status === "idle") {
          this.clearWatchdog();
          if (this.currentState !== "SPEAKING" && this.currentState !== "RECORDING") {
            if (this.isConversationActive) {
              this.setState("LISTENING");
            } else {
              this.setState("IDLE");
            }
          }
        }
        break;

      case "error":
        this.clearWatchdog();
        this.emitError(message.message || "An error occurred on the server.");
        if (this.isConversationActive) {
          this.setState("LISTENING");
        }
        break;

      default:
        break;
    }
  }

  /**
   * Decodes base64 audio and plays it via HTML5 Audio with Blob URL for zero latency.
   * On completion, automatically returns state to LISTENING.
   */
  private playRimeAudio(base64Data: string, format = "audio/wav") {
    if (!base64Data) return;

    try {
      this.stopCurrentAudio();
      this.setState("SPEAKING");
      this.handlers.forEach((h) => h.onRimeAudioStatus?.("speaking"));

      // Binary conversion to Blob
      const binaryString = window.atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: format });
      const audioUrl = URL.createObjectURL(blob);
      this.currentAudioUrl = audioUrl;

      const audio = new Audio(audioUrl);
      this.currentAudio = audio;

      const cleanup = () => {
        if (this.currentAudioUrl) {
          URL.revokeObjectURL(this.currentAudioUrl);
          this.currentAudioUrl = null;
        }
      };

      audio.onended = () => {
        cleanup();
        this.currentAudio = null;
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("completed"));
        // AUTOMATIC RETURN TO LISTENING
        if (this.isConversationActive) {
          this.setState("LISTENING");
        } else {
          this.setState("IDLE");
        }
      };

      audio.onerror = (e) => {
        cleanup();
        console.error("[VoiceService] Audio playback error:", e);
        this.currentAudio = null;
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("idle"));
        if (this.isConversationActive) {
          this.setState("LISTENING");
        } else {
          this.setState("IDLE");
        }
      };

      audio.play().catch((err) => {
        cleanup();
        console.warn("[VoiceService] Autoplay blocked or interrupted:", err);
        this.currentAudio = null;
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("idle"));
        if (this.isConversationActive) {
          this.setState("LISTENING");
        } else {
          this.setState("IDLE");
        }
      });
    } catch (e) {
      console.error("[VoiceService] Failed to play Rime audio:", e);
      if (this.isConversationActive) {
        this.setState("LISTENING");
      } else {
        this.setState("IDLE");
      }
    }
  }

  public stopCurrentAudio() {
    if (this.currentAudio) {
      try {
        this.currentAudio.onended = null;
        this.currentAudio.onerror = null;
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio.src = "";
      } catch { }
      this.currentAudio = null;
    }
    if (this.currentAudioUrl) {
      try {
        URL.revokeObjectURL(this.currentAudioUrl);
      } catch { }
      this.currentAudioUrl = null;
    }
  }

  /**
   * Starts a continuous hands-free voice session with browser VAD.
   */
  public async startConversation(): Promise<void> {
    if (typeof window === "undefined") return;

    this.connectWebSocket();
    this.stopCurrentAudio();
    this.clearWatchdog();

    if (!navigator.mediaDevices?.getUserMedia) {
      const msg = "Microphone recording is not supported in this browser.";
      this.emitError(msg);
      throw new Error(msg);
    }

    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.currentUtteranceChunks = [];
      this.silenceDurationMs = 0;
      this.speechDurationMs = 0;
      this.isUserSpeaking = false;
      this.isConversationActive = true;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.audioContext = new AudioCtx({ sampleRate: 16000 });
        this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.audioStream);
        // 2048 buffer size gives ~128ms per frame at 16kHz for responsive VAD
        this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);

        this.scriptProcessor.onaudioprocess = (e) => {
          if (!this.isConversationActive) return;

          const channelData = e.inputBuffer.getChannelData(0);
          this.processVadAudioFrame(channelData, 128);
        };

        this.mediaStreamSource.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioContext.destination);
      }

      this.setState("LISTENING");
    } catch (err: any) {
      this.isConversationActive = false;
      console.error("[VoiceService] getUserMedia error:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        const errorMsg =
          "Microphone access is required. Please allow microphone access in your browser settings.";
        this.emitError(errorMsg);
        throw new Error(errorMsg);
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        const errorMsg = "No microphone found. Please connect a microphone and try again.";
        this.emitError(errorMsg);
        throw new Error(errorMsg);
      } else {
        const errorMsg = `Microphone error: ${err.message || "Unable to access microphone"}`;
        this.emitError(errorMsg);
        throw new Error(errorMsg);
      }
    }
  }

  /**
   * Real-time Voice Activity Detection (VAD) with Barge-In and Sustained Silence Detection.
   */
  private processVadAudioFrame(channelData: Float32Array, frameDurationMs: number) {
    let sum = 0;
    for (let i = 0; i < channelData.length; i++) {
      sum += channelData[i] * channelData[i];
    }
    const rms = Math.sqrt(sum / channelData.length);

    // Case 1: Assistant is currently speaking through Rime
    if (this.currentState === "SPEAKING") {
      // Check for Barge-In interruption (strong user voice above speaker audio)
      if (rms > this.BARGE_IN_RMS_THRESHOLD) {
        console.info("[VoiceService] Barge-in detected! Interruping playback.");
        this.stopCurrentAudio();
        this.sendInterruption();

        // Start capturing user's new utterance immediately
        this.setState("RECORDING");
        this.isUserSpeaking = true;
        this.currentUtteranceChunks = [new Float32Array(channelData)];
        this.speechDurationMs = frameDurationMs;
        this.silenceDurationMs = 0;
      }
      return; // Do not record assistant's own voice
    }

    // Case 2: Listening state (waiting for user to speak)
    if (this.currentState === "LISTENING" || (this.currentState === "IDLE" && this.isConversationActive)) {
      if (rms > this.SPEECH_RMS_THRESHOLD) {
        // User speech started!
        this.isUserSpeaking = true;
        this.setState("RECORDING");
        this.currentUtteranceChunks = [new Float32Array(channelData)];
        this.speechDurationMs = frameDurationMs;
        this.silenceDurationMs = 0;
      }
      return;
    }

    // Case 3: User is actively speaking (RECORDING state)
    if (this.currentState === "RECORDING") {
      this.currentUtteranceChunks.push(new Float32Array(channelData));

      if (rms > this.SPEECH_RMS_THRESHOLD) {
        this.speechDurationMs += frameDurationMs;
        this.silenceDurationMs = 0;
      } else {
        // Quiet frame
        this.silenceDurationMs += frameDurationMs;

        // Has the user paused long enough to finalize the utterance?
        if (this.silenceDurationMs >= this.SILENCE_TIMEOUT_MS) {
          if (this.speechDurationMs >= this.MIN_SPEECH_DURATION_MS) {
            // Sustained utterance complete! Finalize and send.
            this.finalizeUtterance();
          } else {
            // Noise or brief mic click: discard and return to listening
            this.currentUtteranceChunks = [];
            this.isUserSpeaking = false;
            this.speechDurationMs = 0;
            this.silenceDurationMs = 0;
            this.setState("LISTENING");
          }
        }
      }
    }
  }

  /**
   * Finalizes the captured user speech, packages 16kHz WAV, and sends to backend.
   */
  private finalizeUtterance() {
    if (this.currentUtteranceChunks.length === 0) {
      this.setState("LISTENING");
      return;
    }

    this.setState("TRANSCRIBING");
    this.setWatchdog(20000, "Understanding timed out. Returning to listening.");

    const totalLen = this.currentUtteranceChunks.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const chunk of this.currentUtteranceChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    this.currentUtteranceChunks = [];
    this.isUserSpeaking = false;
    this.speechDurationMs = 0;
    this.silenceDurationMs = 0;

    const audioBlob = encodeWavPcm16(merged, 16000);
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = (reader.result as string).split(",")[1];
      if (base64String && this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(
          JSON.stringify({
            type: "audio",
            mimeType: "audio/wav",
            data: base64String,
          }),
        );
      } else if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        this.emitError("Server connection is offline. Reconnecting...");
        if (this.isConversationActive) {
          this.setState("LISTENING");
        }
      }
    };
    reader.readAsDataURL(audioBlob);
  }

  /**
   * Cleanly ends the live conversation session.
   */
  public async endConversation(): Promise<void> {
    this.isConversationActive = false;
    this.isUserSpeaking = false;
    this.currentUtteranceChunks = [];
    this.stopCurrentAudio();
    this.clearWatchdog();

    try {
      if (this.scriptProcessor && this.mediaStreamSource) {
        this.mediaStreamSource.disconnect();
        this.scriptProcessor.disconnect();
        this.scriptProcessor.onaudioprocess = null;
        this.scriptProcessor = null;
        this.mediaStreamSource = null;
      }
      if (this.audioContext && this.audioContext.state !== "closed") {
        await this.audioContext.close();
        this.audioContext = null;
      }
    } catch (e) {
      console.warn("[VoiceService] Closing audioContext:", e);
    }

    if (this.audioStream) {
      this.audioStream.getTracks().forEach((t) => t.stop());
      this.audioStream = null;
    }

    this.setState("IDLE");
  }

  /**
   * Reset conversation session and clear task state.
   */
  public resetSession() {
    this.stopCurrentAudio();
    this.clearWatchdog();
    this.currentUtteranceChunks = [];
    this.isUserSpeaking = false;

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "reset" }));
    }
    this.setState("IDLE");
  }

  /**
   * Send interruption to backend.
   */
  public sendInterruption() {
    this.stopCurrentAudio();
    this.clearWatchdog();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "interrupt" }));
    }
    this.setState("USER_INTERRUPTED");
  }

  /**
   * Cancel current task execution.
   */
  public cancelTask() {
    this.stopCurrentAudio();
    this.clearWatchdog();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "cancel" }));
    }
    this.setState("CANCELLED");
  }

  /**
   * Send text directly.
   */
  public sendText(text: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.setState("THINKING");
      this.setWatchdog(20000);
      this.ws.send(
        JSON.stringify({
          type: "transcription",
          text,
          final: true,
        }),
      );
    }
  }

  // Legacy compat aliases
  public startRecording() {
    return this.startConversation();
  }
  public stopRecording() {
    return this.endConversation();
  }
}

export const voiceManager = new VoiceSessionManager();

export async function startVoiceSession(): Promise<void> {
  return voiceManager.startConversation();
}

export async function stopVoiceSession(): Promise<void> {
  return voiceManager.endConversation();
}

export async function sendInterruption(): Promise<void> {
  voiceManager.sendInterruption();
  return Promise.resolve();
}

export function resetVoiceSession(): void {
  voiceManager.resetSession();
}
