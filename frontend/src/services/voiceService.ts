/**
 * Voice Service
 *
 * Manages browser microphone capture (16kHz WAV with MediaRecorder fallback),
 * realtime WebSocket connection to the SUTRA backend, audio streaming,
 * Rime audio playback, dynamic task pipeline updates, and session lifecycle.
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
    IDLE: "Tap microphone to speak",
    LISTENING: "Listening...",
    RECORDING: "Recording voice (tap to send)...",
    TRANSCRIBING: "Transcribing with Sarvam...",
    THINKING: "Thinking...",
    TOOL_RUNNING: "Executing tool...",
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
// Voice Session Manager
// ---------------------------------------------------------------------------
class VoiceSessionManager {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private pcmChunks: Float32Array[] = [];
  private currentAudio: HTMLAudioElement | null = null;
  private currentState: VoiceState = "IDLE";
  private handlers: Set<VoiceEventHandlers> = new Set();
  private reconnectTimer: number | null = null;
  private watchdogTimer: number | null = null;

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

  private setWatchdog(timeoutMs = 15000, errorMsg = "Speech processing timed out. Please try again.") {
    this.clearWatchdog();
    this.watchdogTimer = window.setTimeout(() => {
      if (this.currentState === "TRANSCRIBING" || this.currentState === "THINKING") {
        console.warn("[VoiceService] Watchdog timeout fired.");
        this.emitError(errorMsg);
      }
    }, timeoutMs);
  }

  private emitError(message: string) {
    this.clearWatchdog();
    this.setState("IDLE");
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

      this.ws.onclose = () => {
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
    }, 2500);
  }

  private handleIncomingMessage(message: WsIncomingMessage) {
    switch (message.type) {
      case "transcript":
        this.clearWatchdog();
        if (message.text !== undefined) {
          this.handlers.forEach((h) => h.onTranscript?.(message.text!, message.final ?? true));
          if (message.final) {
            this.setState("THINKING");
            this.setWatchdog(25000, "Agent response timed out. Please try speaking again.");
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
              toolName: message.toolName || message.tool || "Flight Search API",
              requestId: message.requestId || "TASK-0001",
              status: "running",
              isCurrent: message.isCurrent ?? true,
            }),
          );
        } else if (message.event === "TOOL_COMPLETED") {
          this.handlers.forEach((h) =>
            h.onToolEvent?.({
              toolName: message.toolName || message.tool || "Flight Search API",
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
            this.setState("IDLE");
          }
        }
        break;

      case "error":
        this.clearWatchdog();
        this.emitError(message.message || "An error occurred on the server.");
        break;

      default:
        break;
    }
  }

  /**
   * Decodes base64 audio (WAV) and plays it via HTML5 Audio.
   */
  private playRimeAudio(base64Data: string, format = "audio/wav") {
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
        this.currentAudio = null;
        this.setState("IDLE");
        this.handlers.forEach((h) => h.onRimeAudioStatus?.("idle"));
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
      } catch { }
      this.currentAudio = null;
    }
  }

  /**
   * Requests browser microphone permission and begins capturing audio chunks.
   */
  public async startRecording(): Promise<void> {
    if (typeof window === "undefined") return;

    this.connectWebSocket();
    this.stopCurrentAudio();
    this.clearWatchdog();

    if (!navigator.mediaDevices?.getUserMedia) {
      this.emitError("Microphone recording is not supported in this browser.");
      throw new Error("Microphone API not supported.");
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

      this.pcmChunks = [];

      // Attempt to capture 16kHz PCM via Web Audio API
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          this.audioContext = new AudioCtx({ sampleRate: 16000 });
          this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.audioStream);
          this.scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);

          this.scriptProcessor.onaudioprocess = (e) => {
            const channelData = e.inputBuffer.getChannelData(0);
            this.pcmChunks.push(new Float32Array(channelData));
          };

          this.mediaStreamSource.connect(this.scriptProcessor);
          this.scriptProcessor.connect(this.audioContext.destination);
        }
      } catch (err) {
        console.warn("[VoiceService] Web Audio ScriptProcessor fallback to MediaRecorder:", err);
      }

      // Also set up MediaRecorder fallback
      try {
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "audio/ogg";
        this.mediaRecorder = new MediaRecorder(this.audioStream, { mimeType });
        this.mediaRecorder.start(250);
      } catch (recErr) {
        console.warn("[VoiceService] MediaRecorder init:", recErr);
      }

      this.setState("RECORDING");
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
   * Stops microphone recording, encodes audio to standard WAV (or fallback blob),
   * and dispatches payload to backend.
   */
  public async stopRecording(): Promise<void> {
    if (this.currentState !== "RECORDING") {
      return;
    }

    this.setState("TRANSCRIBING");
    this.setWatchdog(18000, "Transcription timed out. Please try speaking again.");

    try {
      // Disconnect script processor
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

    // Stop media tracks
    if (this.audioStream) {
      this.audioStream.getTracks().forEach((t) => t.stop());
      this.audioStream = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        this.mediaRecorder.stop();
      } catch { }
      this.mediaRecorder = null;
    }

    // Package audio
    let audioBlob: Blob | null = null;
    if (this.pcmChunks.length > 0) {
      const totalLen = this.pcmChunks.reduce((acc, c) => acc + c.length, 0);
      const merged = new Float32Array(totalLen);
      let offset = 0;
      for (const chunk of this.pcmChunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }
      this.pcmChunks = [];
      audioBlob = encodeWavPcm16(merged, 16000);
    }

    if (!audioBlob || audioBlob.size < 100) {
      this.clearWatchdog();
      this.setState("IDLE");
      return;
    }

    const mimeType = audioBlob.type || "audio/wav";
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
        this.emitError("Server connection is offline. Please refresh and try again.");
      }
    };
    reader.readAsDataURL(audioBlob);
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
   * Reset conversation session.
   */
  public resetSession() {
    this.stopCurrentAudio();
    this.clearWatchdog();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "reset" }));
    }
    this.setState("IDLE");
  }

  /**
   * Send text transcription directly.
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

export function resetVoiceSession(): void {
  voiceManager.resetSession();
}
