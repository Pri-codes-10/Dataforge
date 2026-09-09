/**
 * Mock task history data.
 *
 * This data is used while the SUTRA backend is not yet connected.
 * When the backend is ready, replace usage of this file with calls to
 * `src/services/taskService.ts`.
 */

import type { TaskHistoryItem, TaskDetail } from "@/types";

export const mockTasks: TaskHistoryItem[] = [
  {
    id: "0284",
    task: "Flight Search",
    type: "Travel",
    status: "Completed",
    language: "Hindi + English",
    started: "10:42 AM",
    duration: "4.2s",
  },
  {
    id: "0285",
    task: "Hotel Search",
    type: "Travel",
    status: "Running",
    language: "English",
    started: "10:31 AM",
    duration: "8.4s",
  },
  {
    id: "0279",
    task: "Customer Lookup",
    type: "Database",
    status: "Cancelled",
    language: "Bengali + English",
    started: "Yesterday",
    duration: "2.1s",
  },
  {
    id: "0278",
    task: "Old Flight Search",
    type: "Travel",
    status: "Stale",
    language: "Hindi",
    started: "Yesterday",
    duration: "3.8s",
  },
];

export const mockTaskDetails: Record<string, TaskDetail> = {
  "0284": {
    id: "0284",
    task: "Flight Search",
    type: "Travel",
    status: "Completed",
    language: "Hindi + English",
    started: "10:42 AM",
    duration: "4.2s",
    conversation: "Hindi + English",
    tool: "Flight Search API",
    entities: { origin: "Kolkata", destination: "Delhi" },
    constraints: { date: "Saturday", budget: "₹6,000" },
    requestId: "req_0284",
    stateVersion: 4,
    firstAudioLatencyMs: 480,
    timeline: [
      "REQUEST_RECEIVED",
      "LANGUAGE_DETECTED",
      "INTENT_EXTRACTED",
      "TOOL_STARTED",
      "CONSTRAINT_UPDATED",
      "STATE_UPDATED",
      "TOOL_COMPLETED",
      "RESPONSE_GENERATED",
      "RIME_STARTED",
      "RIME_COMPLETED",
    ],
  },
};

/** Labels for the TaskPipelineEvent values shown in the execution timeline. */
export const taskPipelineEventLabels: Record<string, string> = {
  REQUEST_RECEIVED: "User request received",
  LANGUAGE_DETECTED: "Language detected",
  INTENT_EXTRACTED: "Intent extracted",
  TOOL_STARTED: "Tool started",
  CONSTRAINT_UPDATED: "Constraint updated",
  STATE_UPDATED: "State updated",
  TOOL_COMPLETED: "Tool completed",
  RESPONSE_GENERATED: "Response generated",
  RIME_STARTED: "Rime voice output started",
  RIME_COMPLETED: "Rime voice output completed",
  STALE_RESULT_REJECTED: "Stale result rejected",
  CANCELLED: "Task cancelled",
  ERROR: "Error",
};
