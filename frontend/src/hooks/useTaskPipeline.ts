/**
 * useTaskPipeline Hook
 *
 * Custom React hook for the Task Pipeline panel on the dashboard.
 * Subscribes to live pipeline events, state updates, and Rime synthesis
 * from the backend WebSocket, falling back to taskService.
 */

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getTaskPipelineSteps,
  getActiveToolExecution,
  getStaleToolExecution,
  getRimeState,
} from "@/services/taskService";
import { voiceManager } from "@/services/voiceService";
import type { TaskPipelineStep, ActiveToolExecution, RimeState, ConversationState } from "@/types";

export const TASK_PIPELINE_QUERY_KEY = ["taskPipeline"] as const;

export function useTaskPipeline() {
  const [isRunning, setIsRunning] = useState(true);
  const [liveSteps, setLiveSteps] = useState<TaskPipelineStep[] | null>(null);
  const [liveRimeStatus, setLiveRimeStatus] = useState<"idle" | "speaking" | "completed">("idle");
  const [liveActiveTool, setLiveActiveTool] = useState<ActiveToolExecution | null>(null);
  const [liveConversationState, setLiveConversationState] = useState<Partial<ConversationState> | null>(null);

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

  useEffect(() => {
    const unsubscribe = voiceManager.subscribe({
      onPipelineEvent: (ev) => {
        if (ev.event === "TOOL_STARTED") {
          setIsRunning(true);
          setLiveActiveTool({
            toolName: ev.label || "Flight Search API",
            requestId: ev.requestId || "req_0284",
            elapsedSeconds: 2.8,
            isCurrent: true,
          });
        } else if (ev.event === "TOOL_COMPLETED") {
          // Tool complete
        } else if (ev.event === "CANCELLED") {
          setIsRunning(false);
        } else if (ev.event === "RIME_STARTED") {
          setLiveRimeStatus("speaking");
        } else if (ev.event === "RIME_COMPLETED") {
          setLiveRimeStatus("completed");
        }

        // Dynamically update steps matching the event
        setLiveSteps((prevSteps) => {
          const base = prevSteps ?? stepsQuery.data ?? [];
          return base.map((s) => {
            if (
              (ev.event === "REQUEST_RECEIVED" && s.id === "1") ||
              (ev.event === "LANGUAGE_DETECTED" && s.id === "2") ||
              (ev.event === "INTENT_EXTRACTED" && s.id === "3") ||
              (ev.event === "TOOL_STARTED" && s.id === "4") ||
              (ev.event === "STATE_UPDATED" && s.id === "5")
            ) {
              return { ...s, status: ev.status === "running" ? "running" : "completed" };
            }
            return s;
          });
        });
      },
      onConversationState: (state) => {
        setLiveConversationState(state);
      },
      onRimeAudioStatus: (status) => {
        setLiveRimeStatus(status);
      },
    });

    return () => unsubscribe();
  }, [stepsQuery.data]);

  const cancelCurrentTask = useCallback(async () => {
    setIsRunning(false);
    voiceManager.cancelTask();
  }, []);

  const interruptCurrentTask = useCallback(async () => {
    voiceManager.sendInterruption();
  }, []);

  const steps = liveSteps ?? stepsQuery.data ?? [];
  const activeTool = liveActiveTool ?? activeToolQuery.data;
  const staleExecution = staleQuery.data;
  const rimeState: RimeState = {
    status: liveRimeStatus ?? rimeQuery.data?.status ?? "idle",
  };

  return {
    steps,
    activeTool,
    staleExecution,
    rimeState,
    conversationState: liveConversationState,
    isRunning,
    cancelTask: cancelCurrentTask,
    interruptTask: interruptCurrentTask,
    isLoading: stepsQuery.isLoading,
  };
}
