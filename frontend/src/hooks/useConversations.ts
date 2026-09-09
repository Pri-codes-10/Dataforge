/**
 * useConversations Hook
 *
 * Custom React hooks for accessing conversation and message data.
 * Consumes `conversationService` exclusively — never imports mock data directly.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getConversations,
  getConversation,
  getRecentConversations,
  createConversation as createConversationService,
  sendMessage as sendMessageService,
} from "@/services/conversationService";
import type { Conversation, Message, RecentConversationGroup } from "@/types";

export const CONVERSATIONS_QUERY_KEY = ["conversations"] as const;
export const RECENT_CONVERSATIONS_QUERY_KEY = ["conversations", "recent"] as const;

/**
 * Hook to retrieve all conversations for the user.
 */
export function useConversations() {
  const queryClient = useQueryClient();

  const query = useQuery<Conversation[], Error>({
    queryKey: CONVERSATIONS_QUERY_KEY,
    queryFn: getConversations,
  });

  const createMutation = useMutation({
    mutationFn: (title?: string) => createConversationService(title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: RECENT_CONVERSATIONS_QUERY_KEY });
    },
  });

  return {
    conversations: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    createConversation: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
  };
}

/**
 * Hook to retrieve a single conversation by ID with its messages.
 */
export function useConversation(conversationId: string) {
  const queryClient = useQueryClient();

  const query = useQuery<Conversation | undefined, Error>({
    queryKey: [...CONVERSATIONS_QUERY_KEY, conversationId],
    queryFn: () => getConversation(conversationId),
    enabled: Boolean(conversationId),
  });

  const sendMutation = useMutation({
    mutationFn: ({ content, language }: { content: string; language?: string | undefined }) =>
      sendMessageService(conversationId, content, language ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...CONVERSATIONS_QUERY_KEY, conversationId] });
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: RECENT_CONVERSATIONS_QUERY_KEY });
    },
  });

  return {
    conversation: query.data,
    messages: query.data?.messages ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    sendMessage: (content: string, language?: string) =>
      sendMutation.mutateAsync({ content, language }),
    isSending: sendMutation.isPending,
  };
}

/**
 * Hook to retrieve grouped recent conversations for the sidebar history.
 */
export function useRecentConversations() {
  const query = useQuery<RecentConversationGroup[], Error>({
    queryKey: RECENT_CONVERSATIONS_QUERY_KEY,
    queryFn: getRecentConversations,
  });

  return {
    recentGroups: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
