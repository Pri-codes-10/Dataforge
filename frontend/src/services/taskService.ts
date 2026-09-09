/**
 * Task Service
 *
 * Provides task execution, pipeline status, and task history data.
 * Currently serves data from isolated mock models in `src/data/`.
 *
 * When the backend is ready, replace mock returns with apiClient calls:
 * e.g. return apiClient.get<TaskHistoryItem[]>("/tasks");
 */

import type {
  TaskHistoryItem,
  TaskDetail,
  TaskPipelineStep,
  ActiveToolExecution,
  RimeState,
} from "@/types";
import { mockTasks, mockTaskDetails } from "@/data/mockTasks";
import {
  mockTaskPipelineSteps,
  mockActiveToolExecution,
  mockStaleToolExecution,
  mockRimeState,
} from "@/data/mockDashboard";
import { taskPipelineEventLabels } from "@/data/mockTasks";

export { taskPipelineEventLabels };


/**
 * Returns all past and active tasks for the current user.
 * Future: GET /tasks
 */
export async function getTasks(): Promise<TaskHistoryItem[]> {
  // TODO: Replace with apiClient.get<TaskHistoryItem[]>("/tasks");
  return Promise.resolve([...mockTasks]);
}

/**
 * Returns detailed execution information for a single task by ID.
 * Future: GET /tasks/:id
 */
export async function getTaskDetail(id: string): Promise<TaskDetail | undefined> {
  // TODO: Replace with apiClient.get<TaskDetail>(`/tasks/${id}`);
  const detail =
    mockTaskDetails[id] ??
    ({
      ...mockTasks.find((t) => t.id === id),
      conversation: "",
      tool: "",
      entities: {},
      constraints: {},
      requestId: `req_${id}`,
      stateVersion: 1,
      timeline: [],
    } as TaskDetail);
  return Promise.resolve(detail ? { ...detail } : undefined);
}

/**
 * Returns the current Task Pipeline steps for the live session.
 * Future: GET /tasks/pipeline
 */
export async function getTaskPipelineSteps(): Promise<TaskPipelineStep[]> {
  // TODO: Replace with live state from backend WebSocket/SSE stream
  return Promise.resolve([...mockTaskPipelineSteps]);
}

/**
 * Returns current active tool execution metadata.
 * Future: GET /tasks/active-tool
 */
export async function getActiveToolExecution(): Promise<ActiveToolExecution> {
  // TODO: Replace with live tool execution event
  return Promise.resolve({ ...mockActiveToolExecution });
}

/**
 * Returns metadata about the latest superseded/stale request.
 * Future: GET /tasks/stale-tool
 */
export async function getStaleToolExecution(): Promise<{ requestId: string; isCurrent: boolean }> {
  return Promise.resolve({ ...mockStaleToolExecution });
}

/**
 * Returns Rime speech synthesis status.
 * Future: GET /voice/rime/status
 */
export async function getRimeState(): Promise<RimeState> {
  return Promise.resolve({ ...mockRimeState });
}

/**
 * Cancels a running task.
 * Future: POST /tasks/:id/cancel
 */
export async function cancelTask(id: string): Promise<void> {
  // TODO: Replace with apiClient.post(`/tasks/${id}/cancel`, {});
  console.info(`[taskService] cancelTask called for ${id} — mock handled`);
  return Promise.resolve();
}

/**
 * Interrupts current task execution.
 * Future: POST /tasks/interrupt
 */
export async function interruptTask(): Promise<void> {
  console.info("[taskService] interruptTask called — mock handled");
  return Promise.resolve();
}
