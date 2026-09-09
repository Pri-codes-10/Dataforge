/**
 * Mock conversation data.
 *
 * This data is used while the SUTRA backend is not yet connected.
 * When the backend is ready, replace usage of this file with calls to
 * `src/services/conversationService.ts`.
 */

import type { Conversation, Message, ConversationState } from "@/types";

export const mockConversations: Conversation[] = [
  {
    id: "flight-search",
    title: "Flight Search",
    lastMessage: "Mujhe Kolkata se Delhi jaana hai...",
    languages: "Hindi + English",
    status: "Completed",
    time: "Today, 10:42 AM",
    messages: [
      {
        id: "msg-1",
        role: "user",
        content: "Mujhe Kolkata se Delhi jaana hai, kal ke liye under ₹6,000.",
        language: "Hindi + English",
        timestamp: "2026-09-09T10:42:00Z",
      },
      {
        id: "msg-2",
        role: "assistant",
        content: "I'm searching for flights from Kolkata to Delhi tomorrow under ₹6,000.",
        timestamp: "2026-09-09T10:42:04Z",
      },
      {
        id: "msg-3",
        role: "user",
        content: "Actually Saturday ko chahiye.",
        language: "Hindi + English",
        wasInterruption: true,
        timestamp: "2026-09-09T10:42:08Z",
      },
      {
        id: "msg-4",
        role: "assistant",
        content:
          "Updated to Saturday. I rejected the earlier result and continued with your new constraint.",
        timestamp: "2026-09-09T10:42:12Z",
      },
    ],
    state: {
      intent: "flight_search",
      language: ["Hindi", "English"],
      codeSwitched: true,
      entities: { origin: "Kolkata", destination: "Delhi" },
      constraints: { date: "Saturday", max_price: 6000 },
      activeTask: "TASK-0284",
      stateVersion: 4,
    },
  },
  {
    id: "hotel-search",
    title: "Hotel Search",
    lastMessage: "Find me a hotel near Delhi Airport...",
    languages: "English",
    status: "Completed",
    time: "Yesterday",
    messages: [
      {
        id: "msg-5",
        role: "user",
        content: "Find me a hotel near Delhi Airport under ₹4,000 per night.",
        language: "English",
        timestamp: "2026-09-08T14:30:00Z",
      },
    ],
    state: {
      intent: "hotel_search",
      language: ["English"],
      codeSwitched: false,
      entities: { location: "Delhi Airport" },
      constraints: { max_price_per_night: 4000 },
      activeTask: null,
      stateVersion: 2,
    },
  },
  {
    id: "restaurant-search",
    title: "Restaurant Search",
    lastMessage: "Cheap 5 star restaurants nearby...",
    languages: "Bengali + English",
    status: "Running",
    time: "Monday",
    messages: [
      {
        id: "msg-6",
        role: "user",
        content: "Cheap 5 star restaurants nearby dikha.",
        language: "Bengali + English",
        timestamp: "2026-09-07T19:15:00Z",
      },
    ],
    state: {
      intent: "restaurant_search",
      language: ["Bengali", "English"],
      codeSwitched: true,
      entities: {},
      constraints: { category: "5-star", price: "cheap" },
      activeTask: "TASK-0285",
      stateVersion: 1,
    },
  },
];

export const mockConversationState: ConversationState = {
  intent: "flight_search",
  language: ["Hindi", "English"],
  codeSwitched: true,
  entities: { origin: "Kolkata", destination: "Delhi" },
  constraints: { date: "Saturday", max_price: 6000 },
  activeTask: "TASK-0284",
  stateVersion: 4,
};

export const mockMessages: Message[] = mockConversations[0]?.messages ?? [];
