/**
 * Conversation Service
 *
 * Provides real Redis-backed conversation and chat session data to the application.
 * Interacts directly with the FastAPI backend REST API.
 */

import type { Conversation, Message, RecentConversationGroup } from "@/types";
import { apiClient } from "@/services/apiClient";
import { voiceManager } from "@/services/voiceService";

/**
 * Returns all conversations stored in Redis.
 */
export async function getConversations(): Promise<Conversation[]> {
  try {
    const data = await apiClient.get<Conversation[]>("/api/conversations");
    return data || [];
  } catch (err) {
    console.warn("[ConversationService] Failed to fetch conversations from backend:", err);
    return [];
  }
}

/**
 * Returns a single conversation by ID with its messages and active state.
 */
export async function getConversation(id: string): Promise<Conversation | undefined> {
  try {
    const data = await apiClient.get<Conversation>(`/api/conversations/${encodeURIComponent(id)}`);
    return data;
  } catch (err) {
    console.warn(`[ConversationService] Failed to fetch conversation ${id}:`, err);
    return undefined;
  }
}

/**
 * Returns grouped recent conversation history items for the sidebar.
 */
export async function getRecentConversations(): Promise<RecentConversationGroup[]> {
  try {
    const data = await apiClient.get<RecentConversationGroup[]>("/api/conversations/recent");
    return data || [];
  } catch (err) {
    console.warn("[ConversationService] Failed to fetch recent conversations:", err);
    return [];
  }
}

/**
 * Creates a new conversation session in Redis.
 */
export async function createConversation(title = "New Conversation"): Promise<Conversation> {
  try {
    const data = await apiClient.post<Conversation>("/api/conversations", { title });
    // Save new conversation ID to localStorage and update voiceManager
    if (data?.id && typeof window !== "undefined") {
      voiceManager.setConversationId(data.id);
    }
    return data;
  } catch (err) {
    console.error("[ConversationService] Failed to create conversation:", err);
    const fallbackId = `conv-${Date.now()}`;
    if (typeof window !== "undefined") {
      voiceManager.setConversationId(fallbackId);
    }
    return {
      id: fallbackId,
      title,
      lastMessage: "Conversation started",
      languages: "English",
      status: "Running",
      time: "Just now",
      messages: [],
    };
  }
}

/**
 * Adds a new message to a conversation and receives the response.
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  language = "Hindi + English"
): Promise<Message> {
  try {
    const data = await apiClient.post<Message>(
      `/api/conversations/${encodeURIComponent(conversationId)}/messages`,
      { content, language }
    );
    return data;
  } catch (err) {
    console.error(`[ConversationService] Failed to send message to ${conversationId}:`, err);
    return {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      language,
      timestamp: new Date().toISOString(),
    };
  }
}
