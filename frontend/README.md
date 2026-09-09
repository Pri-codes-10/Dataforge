# SUTRA

## Multilingual Real-Time Voice Agent

> "The conversation never loses the thread."

---

## Overview

SUTRA is a multilingual voice-first agent designed to maintain conversation continuity while executing real-time tasks through tools. It handles mid-conversation language switches, user interruptions, dynamic constraint updates, and stale-result protection — all without losing the thread of what the user originally asked.

The current repository contains the **frontend only**. Backend integration will be added separately.

---

## Core Capabilities

| Capability | Description |
|---|---|
| **Multilingual speech** | Understands and responds in Hindi, English, Bengali, Sanskrit, Tamil, and more |
| **Code-switched conversation** | Handles natural mixing of languages within a single utterance |
| **Conversation continuity** | Maintains full intent, entities, and constraint state across turns |
| **Long-running tool execution** | Executes tools (e.g. flight search, hotel search) while the conversation continues |
| **Dynamic constraint updates** | User can update constraints mid-task ("actually, make it Saturday") |
| **User interruption** | User can speak while the agent is speaking; SUTRA updates and continues |
| **Task state management** | Tracks task versions, active requests, and completed results |
| **Stale-result protection** | Rejects results from superseded requests to prevent state corruption |
| **Rime-powered voice output** | Uses Rime as the voice synthesis engine |

---

## Frontend Technology Stack

| Technology | Version | Description |
|---|---|---|
| **React** | 19 | UI framework |
| **TanStack Start** | 1.168.x | SSR meta-framework |
| **TanStack Router** | 1.170.x | Type-safe file-based routing |
| **TanStack Query** | 5.x | Server state management and caching |
| **Vite** | 8.x | Frontend build tool |
| **TailwindCSS** | 4.x | Styling and design tokens |
| **shadcn/ui** | New York | Accessible UI primitives |
| **TypeScript** | 5.8 | Strict type checking and data contracts |
| **Lucide React** | Icons | Consistent UI iconography |
| **Nunito Sans** | Typography | Google Font typography |
| **Recharts** | Charts | Data visualization |
| **Sonner** | Notifications | Toast alerts |
| **Zod** | Schema validation | Runtime schema verification |

---

## Pages & Routes

| Page | Route | Description |
|---|---|---|
| **Dashboard** | `/` | Live voice session with animated voice orb, language detection panel, and real-time task pipeline |
| **Conversations** | `/conversations` | List of past conversations with language, status, and last message preview |
| **Conversation Detail** | `/conversations/:id` | Full message thread with user interruptions and conversation state |
| **Task History** | `/tasks` | Table of all executed tasks with status badges and execution metrics |
| **Task Detail** | `/tasks/:id` | Full execution timeline and detail for a single task |
| **Settings** | `/settings` | Voice engine, language preferences, conversation behavior, task execution, and appearance |

---

## Architecture & Separation of Concerns

The codebase enforces a strict unidirectional layered architecture:

```
[ UI Components ]
        ↓ (calls custom hooks)
[ Custom Hooks (src/hooks/) ]
        ↓ (calls service functions)
[ Service Layer (src/services/) ]
        ↓ (apiClient with VITE_API_URL / isolated mock data)
[ Data Contracts (src/types/) ]
        ↓ (future connection)
[ SUTRA Backend / WebSocket ]
```

### Key Architectural Rules
1. **Components never import mock data directly**: All UI components consume custom hooks (`src/hooks/`).
2. **Hooks consume services**: Hooks wrap TanStack Query (`useQuery`, `useMutation`) or local React state around service methods.
3. **Services encapsulate data access**: Currently, services return data conforming to `src/types/index.ts` from isolated mock files in `src/data/`. When a backend is introduced, only the services need to be updated to call `apiClient` or establish WebSocket connections.
4. **Centralized Configuration**: All environment variables and backend endpoints are read from `src/config.ts` (`VITE_API_URL`).
5. **Clean Error Hierarchy**: Standardized typed errors (`NetworkError`, `ValidationError`, `ToolError`, `VoiceError`) in `src/types/index.ts` and `src/services/apiClient.ts`.

---

## Directory Structure

```
src/
├── assets/             # Brand assets (logo.ico)
├── components/
│   ├── sutra/          # SUTRA application components (AppShell, Dashboard, Pages)
│   └── ui/             # shadcn/ui primitives (button, input, select, etc.)
├── config.ts           # Centralized configuration (reads VITE_API_URL)
├── data/               # Isolated mock data (accessed ONLY by src/services/)
│   ├── mockConversations.ts
│   ├── mockDashboard.ts
│   └── mockTasks.ts
├── hooks/              # Custom React hooks (UI consumes these)
│   ├── index.ts
│   ├── useConversations.ts
│   ├── useLanguageDetection.ts
│   ├── useSettings.ts
│   ├── useTaskPipeline.ts
│   ├── useTasks.ts
│   └── useVoiceSession.ts
├── lib/                # Utilities (cn, error-reporting)
├── routes/             # File-based routes (TanStack Router)
├── services/           # Service layer & API client
│   ├── apiClient.ts
│   ├── conversationService.ts
│   ├── languageService.ts
│   ├── settingsService.ts
│   ├── taskService.ts
│   └── voiceService.ts
├── types/              # Pure TypeScript data contracts
│   └── index.ts
└── styles.css          # Design tokens, keyframe animations, dark/light themes
```

---

## Development

### Install dependencies

```bash
npm install
```

### Start the development server

```bash
npm run dev
```

The app will be available at `http://localhost:8080`.

### Type check

```bash
npx tsc --noEmit
```

### Build for production

```bash
npm run build
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

| Variable | Description | Default / Fallback |
|---|---|---|
| `VITE_API_URL` | Base URL for the SUTRA backend API | `http://localhost:8000/api/v1` (runs with mock services when empty or unreachable) |

---

## Future Backend Integration Guide

The frontend has been prepared to connect to a future backend with **zero UI changes**:

### Step 1: Provide Backend URL
Set `VITE_API_URL` in your `.env` file:
```bash
VITE_API_URL=https://api.sutra.ai/v1
```

### Step 2: Switch Services from Mock Data to `apiClient`
In `src/services/conversationService.ts`:
```ts
// Switch from mock to real HTTP endpoint:
export async function getConversations(): Promise<Conversation[]> {
  return apiClient.get<Conversation[]>("/conversations");
}
```

In `src/services/taskService.ts`:
```ts
export async function getTasks(): Promise<TaskHistoryItem[]> {
  return apiClient.get<TaskHistoryItem[]>("/tasks");
}
```

### Step 3: Connect Voice Session
In `src/services/voiceService.ts`, connect to your backend's WebSocket or SSE endpoint:
```ts
export async function startVoiceSession(): Promise<void> {
  const ws = new WebSocket(`${config.apiUrl.replace('http', 'ws')}/voice/session`);
  // Handle audio stream and voice events
}
```

### Data Contracts
All contracts are formally defined in `src/types/index.ts`:
- `VoiceState`: `IDLE` | `LISTENING` | `TRANSCRIBING` | `THINKING` | `TOOL_RUNNING` | `USER_INTERRUPTED` | `TASK_UPDATED` | `SPEAKING` | `CANCELLED` | `ERROR` | `STALE_RESULT_REJECTED`
- `ConversationState`: `intent`, `language`, `codeSwitched`, `entities`, `constraints`, `activeTask`, `stateVersion`
- `TaskPipelineStep`: `id`, `label`, `status` (`pending` | `running` | `completed` | `failed` | `cancelled` | `stale`), `durationSeconds`
- `LanguageDetection`: `detectedLanguages`, `activeLanguages`, `codeSwitched`, `confidence`, `label`
- `AppSettings`: Voice, language, conversation, task execution, and appearance preferences

---

## License

MIT
