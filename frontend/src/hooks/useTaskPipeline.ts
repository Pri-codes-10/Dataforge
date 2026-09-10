/**
 * useTaskPipeline Hook
 *
 * Custom React hook for the dynamic Task Pipeline panel on the dashboard.
 * Subscribes to live pipeline events, state updates, tool executions,
 * stale result rejections, Rime synthesis, and reset events.
 */

import { useState, useEffect, useCallback } from "react";
import { voiceManager } from "@/services/voiceService";
import type { TaskPipelineStep, ActiveToolExecution, RimeState, ConversationState } from "@/types";

const initialDefaultSteps: TaskPipelineStep[] = [
  { id: "understand", label: "Understand request", status: "pending" },
  { id: "tool", label: "Execute task", status: "pending" },
  { id: "response", label: "Generate response", status: "pending" },
  { id: "rime", label: "Rime voice output", status: "pending" },
];

export function useTaskPipeline() {
  const [isRunning, setIsRunning] = useState(false);
  const [steps, setSteps] = useState<TaskPipelineStep[]>(initialDefaultSteps);
  const [activeTool, setActiveTool] = useState<ActiveToolExecution | null>(null);
  const [staleExecution, setStaleExecution] = useState<{ requestId: string; isCurrent: boolean; message?: string } | null>(null);
  const [rimeStatus, setRimeStatus] = useState<"idle" | "speaking" | "completed">("idle");
  const [conversationState, setConversationState] = useState<Partial<ConversationState> | null>(null);

  useEffect(() => {
    const unsubscribe = voiceManager.subscribe({
      onPipelineSteps: (newSteps, running) => {
        setSteps(newSteps);
        setIsRunning(running);
      },

      onToolEvent: (tool) => {
        setIsRunning(tool.status === "running");
        setActiveTool({
          toolName: tool.toolName,
          requestId: tool.requestId,
          elapsedSeconds: 1.5,
          isCurrent: tool.isCurrent,
        });
      },

      onStaleResult: (stale) => {
        setStaleExecution({
          requestId: stale.requestId,
          isCurrent: false,
          message: stale.message,
        });
        setIsRunning(false);
      },

      onPipelineEvent: (ev) => {
        if (ev.event === "TOOL_STARTED") {
          setIsRunning(true);
          setActiveTool({
            toolName: ev.label || ev.tool || "Task Execution API",
            requestId: ev.requestId || "TASK-0001",
            elapsedSeconds: 0.0,
            isCurrent: true,
          });
        } else if (ev.event === "TOOL_COMPLETED") {
          setIsRunning(false);
        } else if (ev.event === "STALE_RESULT_REJECTED") {
          setStaleExecution({
            requestId: ev.requestId || "TASK-0001",
            isCurrent: false,
            message: "Stale result rejected",
          });
          setIsRunning(false);
        } else if (ev.event === "CANCELLED" || ev.event === "SESSION_RESET") {
          setIsRunning(false);
          setActiveTool(null);
          if (ev.event === "SESSION_RESET") {
            setStaleExecution(null);
            setSteps(initialDefaultSteps);
          }
        } else if (ev.event === "RIME_STARTED") {
          setRimeStatus("speaking");
        } else if (ev.event === "RIME_COMPLETED") {
          setRimeStatus("completed");
        }
      },

      onResetComplete: () => {
        setIsRunning(false);
        setActiveTool(null);
        setStaleExecution(null);
        setSteps(initialDefaultSteps);
        setRimeStatus("idle");
      },

      onConversationState: (state) => {
        setConversationState(state);
      },

      onRimeAudioStatus: (status) => {
        setRimeStatus(status);
        if (status === "completed" || status === "idle") {
          setIsRunning(false);
        }
      },
    });

    return () => unsubscribe();
  }, []);

  const cancelCurrentTask = useCallback(async () => {
    setIsRunning(false);
    voiceManager.cancelTask();
  }, []);

  const interruptCurrentTask = useCallback(async () => {
    voiceManager.sendInterruption();
  }, []);

  const rimeState: RimeState = {
    status: rimeStatus,
  };

  return {
    steps,
    activeTool,
    staleExecution,
    rimeState,
    conversationState,
    isRunning,
    cancelTask: cancelCurrentTask,
    interruptTask: interruptCurrentTask,
    isLoading: false,
  };
}
