/**
 * Mock dashboard data.
 *
 * This data is used while the SUTRA backend is not yet connected.
 * When the backend is ready, replace usage of this file with calls to
 * the appropriate service (voiceService, languageService, etc.).
 */

import type { LanguageDetection, TaskPipelineStep, ConversationState, RimeState } from "@/types";

export const mockLanguageDetection: LanguageDetection = {
  detectedLanguages: ["English", "Bengali", "Hindi", "Sanskrit"],
  activeLanguages: ["English", "Hindi"],
  codeSwitched: true,
  label: "Hindi + English",
};

export const mockTaskPipelineSteps: TaskPipelineStep[] = [
  { id: "understand", label: "Understand request", status: "completed" },
  { id: "search", label: "Search flights", status: "running", durationSeconds: 2.8 },
  { id: "response", label: "Generate response", status: "pending" },
  { id: "rime", label: "Rime voice output", status: "pending" },
];

export const mockDashboardConversationState: ConversationState = {
  intent: "flight_search",
  language: ["Hindi", "English"],
  codeSwitched: true,
  entities: { origin: "Kolkata", destination: "Delhi" },
  constraints: { date: "Saturday", max_price: 6000 },
  activeTask: "TASK-0284",
  stateVersion: 4,
};

export const mockRimeState: RimeState = {
  status: "speaking",
};

export interface RecentConversationItem {
  id: string;
  title: string;
  time: string;
}

export interface RecentConversationGroup {
  group: string;
  items: RecentConversationItem[];
}

/** Recent conversation sidebar items — shown in the app shell sidebar. */
export const mockRecentConversations: RecentConversationGroup[] = [
  {
    group: "Today",
    items: [
      { id: "hotel-search", title: "Hotels near Delhi Airport", time: "10:42 AM" },
      { id: "flight-search", title: "Flights Mumbai to Delhi", time: "9:15 AM" },
    ],
  },
  {
    group: "Yesterday",
    items: [
      { id: "restaurant-search", title: "Cheap 5 star restaurants", time: "Yesterday" },
    ],
  },
];

/**
 * The active tool execution shown in the Task Pipeline panel.
 * Represents request #0284 which is currently running.
 */
export const mockActiveToolExecution = {
  requestId: "0284",
  toolName: "Flight Search API",
  elapsedSeconds: 2.8,
  isCurrent: true,
};

/**
 * The stale tool execution shown in the Task Pipeline panel.
 * Represents request #0283 which was superseded.
 */
export const mockStaleToolExecution = {
  requestId: "0283",
  isCurrent: false,
};
