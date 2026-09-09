/**
 * SUTRA Frontend — TypeScript Data Contracts
 *
 * These interfaces define the frontend data contracts. They are designed to
 * be populated from the SUTRA backend via apiClient and custom hooks.
 * Currently the application services supply mock data that strictly conforms
 * to these types.
 *
 * Do NOT import backend implementation details here — these are pure frontend
 * contracts that mirror the shape of the backend's API responses.
 */

// ---------------------------------------------------------------------------
// Voice State
// ---------------------------------------------------------------------------

/**
 * The current state of the SUTRA voice session.
 * Maps to the voice UI animation states and microphone button label.
 */
export type VoiceState =
  | "IDLE"
  | "LISTENING"
  | "RECORDING"
  | "TRANSCRIBING"
  | "THINKING"
  | "TOOL_RUNNING"
  | "USER_INTERRUPTED"
  | "TASK_UPDATED"
  | "SPEAKING"
  | "CANCELLED"
  | "ERROR"
  | "STALE_RESULT_REJECTED";

// ---------------------------------------------------------------------------
// Language & Language Detection
// ---------------------------------------------------------------------------

export type SupportedLanguage = "English" | "Hindi" | "Bengali" | "Sanskrit" | "Tamil" | "Telugu" | string;

export interface LanguageDetection {
  /** All languages detected in the current session. */
  detectedLanguages: string[];
  /** The primary language inferred or selected. */
  primaryLanguage?: string;
  /** The language(s) actively selected / confirmed. */
  activeLanguages: string[];
  /** True if the user is code-switching between languages. */
  codeSwitched: boolean;
  /** Model confidence score for detection (0 to 1). */
  confidence?: number;
  /** Human-readable combined label e.g. "Hindi + English". */
  label: string;
}

// ---------------------------------------------------------------------------
// Conversation State
// ---------------------------------------------------------------------------

export type EntityValue = string | number | boolean | null;
export type EntityMap = Record<string, string>;
export type ConstraintMap = Record<string, string | number>;

/**
 * The structured conversation state maintained by SUTRA across turns.
 * This is what the backend returns and the frontend displays.
 */
export interface ConversationState {
  intent: string | null;
  language: string[];
  codeSwitched: boolean;
  entities: EntityMap;
  constraints: ConstraintMap;
  activeTask: string | null;
  stateVersion: number;
}

// ---------------------------------------------------------------------------
// Task Pipeline
// ---------------------------------------------------------------------------

export type TaskPipelineEvent =
  | "REQUEST_RECEIVED"
  | "LANGUAGE_DETECTED"
  | "INTENT_EXTRACTED"
  | "TOOL_STARTED"
  | "CONSTRAINT_UPDATED"
  | "STATE_UPDATED"
  | "TOOL_COMPLETED"
  | "RESPONSE_GENERATED"
  | "RIME_STARTED"
  | "RIME_COMPLETED"
  | "STALE_RESULT_REJECTED"
  | "CANCELLED"
  | "ERROR";

export type TaskPipelineStepStatus = "pending" | "running" | "completed" | "failed" | "cancelled" | "stale";

export interface TaskPipelineStep {
  id: string;
  label: string;
  status: TaskPipelineStepStatus;
  /** Elapsed duration in seconds, if applicable. */
  durationSeconds?: number;
}

export interface ActiveToolExecution {
  /** The tool/API being called. */
  toolName: string;
  /** The internal request ID. */
  requestId: string;
  /** How long the tool has been running (seconds). */
  elapsedSeconds: number;
  /** Whether this execution is the latest (not stale). */
  isCurrent: boolean;
}

// ---------------------------------------------------------------------------
// Rime (Voice Output Engine)
// ---------------------------------------------------------------------------

export type RimeStatus = "idle" | "speaking" | "completed" | "error";

export interface RimeState {
  status: RimeStatus;
  text?: string;
  audioUrl?: string;
  startedAt?: string;
  completedAt?: string;
}

// ---------------------------------------------------------------------------
// Tool Execution
// ---------------------------------------------------------------------------

export type ToolStatus = "pending" | "running" | "completed" | "cancelled" | "stale" | "error";

export interface ToolExecution {
  id: string;
  toolName: string;
  requestId: string;
  startedAt: string;
  completedAt?: string;
  status: ToolStatus;
  stateVersion?: number;
  result?: ToolResult;
}

export interface ToolResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

// ---------------------------------------------------------------------------
// Conversations & Messages
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  language?: string;
  /** True if the user interrupted the agent mid-response. */
  wasInterruption?: boolean;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  /** Preview of the last message. */
  lastMessage: string;
  /** Human-readable language label e.g. "Hindi + English". */
  languages: string;
  status: "Completed" | "Running" | "Cancelled" | "Failed";
  /** Human-readable timestamp e.g. "Today, 10:42 AM". */
  time: string;
  messages?: Message[];
  state?: ConversationState;
}

export interface RecentConversationItem {
  id: string;
  title: string;
  time: string;
}

export interface RecentConversationGroup {
  group: string;
  items: RecentConversationItem[];
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export type TaskStatus = "Completed" | "Running" | "Cancelled" | "Failed" | "Stale";

export interface Task {
  id: string;
  type: string;
  status: TaskStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface TaskHistoryItem {
  id: string;
  task: string;
  type: string;
  status: TaskStatus;
  language: string;
  started: string;
  duration: string;
}

export interface TaskDetail extends TaskHistoryItem {
  conversation: string;
  tool: string;
  entities: Record<string, string>;
  constraints: Record<string, string | number>;
  requestId: string;
  stateVersion: number;
  firstAudioLatencyMs?: number;
  /** Ordered timeline of events for this task. */
  timeline: TaskPipelineEvent[];
}

// ---------------------------------------------------------------------------
// Agent Response
// ---------------------------------------------------------------------------

export interface AgentResponse {
  conversationId: string;
  messageId: string;
  content: string;
  language: string;
  audioUrl?: string;
  stateVersion: number;
  activeTask?: string | null;
  taskUpdated?: boolean;
}

// ---------------------------------------------------------------------------
// App Settings
// ---------------------------------------------------------------------------

export interface AppSettings {
  voice: {
    engine: "rime" | "native" | string;
    speed: number;
    pitch: number;
    accent: string;
  };
  language: {
    primary: string;
    secondary: string;
    autoDetectCodeSwitching: boolean;
  };
  conversation: {
    retainContextTurns: number;
    staleResultProtection: boolean;
    interruptible: boolean;
  };
  taskExecution: {
    maxTimeoutSeconds: number;
    notifyOnCompletion: boolean;
  };
  appearance: {
    theme: "system" | "dark" | "light";
    reducedMotion: boolean;
  };
}

// ---------------------------------------------------------------------------
// Error Hierarchy
// ---------------------------------------------------------------------------

export type ErrorType =
  | "NETWORK_ERROR"
  | "VALIDATION_ERROR"
  | "TOOL_ERROR"
  | "VOICE_ERROR"
  | "UNKNOWN_ERROR";

export interface AppError {
  type: ErrorType;
  message: string;
  code?: number | string;
  details?: unknown;
}
