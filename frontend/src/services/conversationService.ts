/**
 * Conversation Service
 *
 * Provides conversation and chat session data to the application.
 * Currently serves data from isolated mock models in `src/data/`.
 *
 * When the backend is ready, replace the mock returns with apiClient calls:
 * e.g. return apiClient.get<Conversation[]>("/conversations");
 */

import type { Conversation, Message, RecentConversationGroup } from "@/types";
import { mockConversations } from "@/data/mockConversations";
import { mockRecentConversations } from "@/data/mockDashboard";

/**
 * Returns all conversations for the active user.
 * Future: GET /conversations
 */
export async function getConversations(): Promise<Conversation[]> {
  // TODO: Replace with apiClient.get<Conversation[]>("/conversations");
  return Promise.resolve([...mockConversations]);
}

/**
 * Returns a single conversation by ID, or undefined if not found.
 * Future: GET /conversations/:id
 */
export async function getConversation(id: string): Promise<Conversation | undefined> {
  // TODO: Replace with apiClient.get<Conversation>(`/conversations/${id}`);
  const item = mockConversations.find((c) => c.id === id);
  return Promise.resolve(item ? { ...item } : undefined);
}

/**
 * Returns grouped recent conversation history items for the sidebar.
 * Future: GET /conversations/recent
 */
export async function getRecentConversations(): Promise<RecentConversationGroup[]> {
  // TODO: Replace with apiClient.get<RecentConversationGroup[]>("/conversations/recent");
  return Promise.resolve([...mockRecentConversations]);
}

/**
 * Creates a new conversation session.
 * Future: POST /conversations
 */
export async function createConversation(title = "New Conversation"): Promise<Conversation> {
  const newConversation: Conversation = {
    id: `conv-${Date.now()}`,
    title,
    lastMessage: "Conversation started",
    languages: "Hindi + English",
    status: "Running",
    time: "Just now",
    messages: [],
  };
  // In-memory update for mock runtime
  mockConversations.unshift(newConversation);
  return Promise.resolve(newConversation);
}

/**
 * Adds a new message to a conversation.
 * Future: POST /conversations/:id/messages
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  language = "Hindi + English"
): Promise<Message> {
  const message: Message = {
    id: `msg-${Date.now()}`,
    role: "user",
    content,
    language,
    timestamp: new Date().toISOString(),
  };

  const conv = mockConversations.find((c) => c.id === conversationId);
  if (conv) {
    conv.messages = conv.messages ?? [];
    conv.messages.push(message);
    conv.lastMessage = content;
  }

  return Promise.resolve(message);
}
