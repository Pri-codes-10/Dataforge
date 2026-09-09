/**
 * useTaskPipeline Hook
 *
 * Custom React hook for the Task Pipeline panel on the dashboard.
 * Consumes `taskService` exclusively.
 */

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getTaskPipelineSteps,
  getActiveToolExecution,
  getStaleToolExecution,
  getRimeState,
  cancelTask as cancelTaskService,
  interruptTask as interruptTaskService,
} from "@/services/taskService";
import type { TaskPipelineStep, ActiveToolExecution, RimeState } from "@/types";

export const TASK_PIPELINE_QUERY_KEY = ["taskPipeline"] as const;

export function useTaskPipeline() {
  const [isRunning, setIsRunning] = useState(true);

  const stepsQuery = useQuery<TaskPipelineStep[], Error>({
    queryKey: [...TASK_PIPELINE_QUERY_KEY, "steps"],
    queryFn: getTaskPipelineSteps,
  });

  const activeToolQuery = useQuery<ActiveToolExecution, Error>({
    queryKey: [...TASK_PIPELINE_QUERY_KEY, "activeTool"],
    queryFn: getActiveToolExecution,
  });

  const staleQuery = useQuery<{ requestId: string; isCurrent: boolean }, Error>({
    queryKey: [...TASK_PIPELINE_QUERY_KEY, "staleTool"],
    queryFn: getStaleToolExecution,
  });

  const rimeQuery = useQuery<RimeState, Error>({
    queryKey: [...TASK_PIPELINE_QUERY_KEY, "rime"],
    queryFn: getRimeState,
  });

  const cancelCurrentTask = useCallback(
    async (taskId?: string) => {
      setIsRunning(false);
      await cancelTaskService(taskId ?? "0284");
    },
    [],
  );

  const interruptCurrentTask = useCallback(async () => {
    await interruptTaskService();
  }, []);

  return {
    steps: stepsQuery.data ?? [],
    activeTool: activeToolQuery.data,
    staleExecution: staleQuery.data,
    rimeState: rimeQuery.data,
    isRunning,
    cancelTask: cancelCurrentTask,
    interruptTask: interruptCurrentTask,
    isLoading: stepsQuery.isLoading,
  };
}
