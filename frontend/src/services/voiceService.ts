/**
 * Voice Service
 *
 * Manages browser microphone capture, realtime WebSocket connection to the SUTRA backend,
 * audio streaming, Rime audio playback, and session lifecycle.
 */

import { config } from "@/config";
import type { VoiceState, TaskPipelineStep, ConversationState } from "@/types";

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
    IDLE: "Tap microphone to speak",
    LISTENING: "Listening...",
    RECORDING: "Recording voice (tap to send)...",
    TRANSCRIBING: "Transcribing with Sarvam...",
    THINKING: "Thinking...",
    TOOL_RUNNING: "Working...",
    USER_INTERRUPTED: "Interrupted",
    TASK_UPDATED: "Task updated",
    SPEAKING: "SUTRA is speaking...",
    CANCELLED: "Cancelled",
    ERROR: "Error occurred",
    STALE_RESULT_REJECTED: "Retrying...",
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
  onLanguage?: (lang: string, codeSwitched: boolean) => void;
  onPipelineEvent?: (event: {
    event: string;
    label: string;
    status?: string | undefined;
    tool?: string | undefined;
    requestId?: string | undefined;
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
  event?: string;
  label?: string;
  status?: string;
  tool?: string;
  requestId?: string;
  data?: any;
  format?: string;
  message?: string;
}

class VoiceSessionManager {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private recordedChunks: Blob[] = [];
  private currentAudio: HTMLAudioElement | null = null;
  private currentState: VoiceState = "IDLE";
  private handlers: Set<VoiceEventHandlers> = new Set();
  private reconnectTimer: number | null = null;

  constructor() {
    // Lazy connect WebSocket in browser environment
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

  private emitError(message: string) {
    this.setState("ERROR");
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
        if (this.currentState === "ERROR") {
          this.setState("IDLE");
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleIncomingMessage(message);
        } catch (e) {
          console.warn("[VoiceService] Non-JSON WS message received:", event.data);
        }
      };

      this.ws.onclose = () => {
        console.info("[VoiceService] WebSocket closed, retrying in 3s...");
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn("[VoiceService] WebSocket error:", err);
      };
    } catch (e) {
      console.error("[VoiceService] Could not establish WebSocket:", e);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connectWebSocket();
    }, 3000);
  }

  private handleIncomingMessage(message: WsIncomingMessage) {
    switch (message.type) {
      case "transcript":
        if (message.text !== undefined) {
          this.handlers.forEach((h) => h.onTranscript?.(message.text!, message.final ?? true));
          if (message.final) {
            this.setState("THINKING");
          }
        }
        break;

      case "language":
        if (message.language !== undefined) {
          this.handlers.forEach((h) => h.onLanguage?.(message.language!, message.code_switched ?? false));
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
          this.setState("CANCELLED");
        } else if (message.event === "USER_INTERRUPTED") {
          this.setState("USER_INTERRUPTED");
        }
        break;

      case "response":
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
        if (message.data) {
          this.playRimeAudio(message.data, message.format ?? "audio/mp3");
        }
        break;

      case "error":
        this.emitError(message.message || "An error occurred on the server.");
        break;

      default:
        break;
    }
  }

  /**
   * Decodes base64 audio and plays it via HTML5 Audio.
   */
  private playRimeAudio(base64Data: string, format = "audio/mp3") {
    if (!base64Data) return;

    try {
      this.stopCurrentAudio();
      this.setState("SPEAKING");
      this.handlers.forEach((h) => h.onRimeAudioStatus?.("speaking"));

      const audioUrl = `data:${format};base64,${base64Data}`;
      const audio = new Audio(audioUrl);
      this.currentAudio = audio;

      audio.onended = () => {
        this.currentAudio = null;
        this.setState("IDLE");
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("completed"));
      };

      audio.onerror = (e) => {
        console.error("[VoiceService] Audio playback error:", e);
        this.currentAudio = null;
        this.setState("IDLE");
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("idle"));
      };

      audio.play().catch((err) => {
        console.warn("[VoiceService] Autoplay blocked or interrupted:", err);
        this.setState("IDLE");
      });
    } catch (e) {
      console.error("[VoiceService] Failed to play Rime audio:", e);
      this.setState("IDLE");
    }
  }

  private stopCurrentAudio() {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch {}
      this.currentAudio = null;
    }
  }

  /**
   * Requests browser microphone permission and begins capturing audio chunks.
   */
  public async startRecording(): Promise<void> {
    if (typeof window === "undefined") return;

    // Make sure WS is ready
    this.connectWebSocket();
    this.stopCurrentAudio();

    if (!navigator.mediaDevices?.getUserMedia) {
      this.emitError("Microphone recording is not supported in this browser.");
      throw new Error("Microphone API not supported.");
    }

    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.recordedChunks = [];

      // Determine supported mime type
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/ogg";

      const recorder = new MediaRecorder(this.audioStream, { mimeType });
      this.mediaRecorder = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      recorder.onstart = () => {
        this.setState("RECORDING");
      };

      recorder.onerror = (err) => {
        console.error("[VoiceService] MediaRecorder error:", err);
        this.emitError("Microphone capture encountered an error.");
      };

      // Collect chunks every 250ms
      recorder.start(250);
    } catch (err: any) {
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
   * Stops microphone recording and dispatches the audio payload to the backend.
   */
  public async stopRecording(): Promise<void> {
    if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
      this.setState("IDLE");
      return;
    }

    return new Promise((resolve) => {
      this.mediaRecorder!.onstop = async () => {
        try {
          // Release microphone tracks
          if (this.audioStream) {
            this.audioStream.getTracks().forEach((t) => t.stop());
            this.audioStream = null;
          }

          if (this.recordedChunks.length === 0) {
            this.setState("IDLE");
            resolve();
            return;
          }

          this.setState("TRANSCRIBING");

          const mimeType = this.mediaRecorder?.mimeType || "audio/webm";
          const audioBlob = new Blob(this.recordedChunks, { type: mimeType });

          // Convert Blob to base64
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64String = (reader.result as string).split(",")[1];
            if (base64String && this.ws && this.ws.readyState === WebSocket.OPEN) {
              this.ws.send(
                JSON.stringify({
                  type: "audio",
                  mimeType,
                  data: base64String,
                }),
              );
            } else if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
              this.emitError("Server connection is offline. Please try again.");
            }
            resolve();
          };
          reader.readAsDataURL(audioBlob);
        } catch (e) {
          console.error("[VoiceService] Error packaging audio:", e);
          this.setState("IDLE");
          resolve();
        }
      };

      this.mediaRecorder?.stop();
    });
  }

  /**
   * Cancel task execution.
   */
  public cancelTask() {
    this.stopCurrentAudio();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "cancel" }));
    }
    this.setState("CANCELLED");
  }

  /**
   * Send interruption to the backend.
   */
  public sendInterruption() {
    this.stopCurrentAudio();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "interrupt" }));
    }
    this.setState("USER_INTERRUPTED");
  }

  /**
   * Send text transcription directly.
   */
  public sendText(text: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "transcription",
          text,
          final: true,
        }),
      );
    }
  }
}

export const voiceManager = new VoiceSessionManager();

export async function startVoiceSession(): Promise<void> {
  return voiceManager.startRecording();
}

export async function stopVoiceSession(): Promise<void> {
  return voiceManager.stopRecording();
}

export async function sendInterruption(): Promise<void> {
  voiceManager.sendInterruption();
  return Promise.resolve();
}
