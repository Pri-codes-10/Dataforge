/**
 * useTasks Hook
 *
 * Custom React hooks for accessing task history and task execution details.
 * Consumes `taskService` exclusively — never imports mock data directly.
 */

import { useQuery } from "@tanstack/react-query";
import { getTasks, getTaskDetail, taskPipelineEventLabels } from "@/services/taskService";
import type { TaskHistoryItem, TaskDetail } from "@/types";

export { taskPipelineEventLabels };


export const TASKS_QUERY_KEY = ["tasks"] as const;

/**
 * Hook to retrieve all task history items.
 */
export function useTasks() {
  const query = useQuery<TaskHistoryItem[], Error>({
    queryKey: TASKS_QUERY_KEY,
    queryFn: getTasks,
  });

  return {
    tasks: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook to retrieve execution details for a specific task.
 */
export function useTaskDetail(taskId: string) {
  const query = useQuery<TaskDetail | undefined, Error>({
    queryKey: [...TASKS_QUERY_KEY, taskId],
    queryFn: () => getTaskDetail(taskId),
    enabled: Boolean(taskId),
  });

  return {
    taskDetail: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
