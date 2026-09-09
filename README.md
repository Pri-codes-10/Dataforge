# SUTRA

Multilingual Real-Time Voice Agent

> "The conversation never loses the thread."

---

## Overview

SUTRA is a multilingual voice-first agent designed to maintain conversational continuity while executing real-time tasks through tools. It handles mid-conversation language switches, user interruptions, dynamic constraint updates, and stale-result protection without losing the context of what the user originally requested.

The application integrates a modern React frontend with a FastAPI backend, Sarvam AI Speech-to-Text (Saarika), Sarvam LLM conversation agent, and Rime Text-to-Speech (TTS) voice synthesis.

---

## Core Features

- **Browser Microphone Audio Capture:** Real microphone capture via browser `navigator.mediaDevices.getUserMedia` and `MediaRecorder`.
- **Server-Side Multilingual STT:** Powered by Sarvam AI Saarika (`saarika:v2.5`), converting Hindi, English, Bengali, and code-mixed Hinglish into text.
- **Multilingual & Code-Switching Detection:** Detects script, vocabulary, and code-switching dynamically without requiring the user to pre-select a language.
- **Continuous Conversation State:** Retains session intent, entities, constraints, and versioning across multiple conversation turns.
- **Real-Time Task Pipeline:** Tracks request reception, intent extraction, tool execution, and response synthesis over WebSocket.
- **Stale Result Protection:** Rejects results from superseded requests to prevent outdated task responses from overwriting the latest conversation state.
- **Rime Voice Output:** Converts assistant responses to spoken speech via Rime TTS with frontend audio playback.

---

## Architecture

```
User (Microphone)
       ↓ (Audio chunks: webm/opus)
Frontend (useVoiceSession / voiceService)
       ↓ (WebSocket /ws/voice)
FastAPI Backend (app/api/websocket.py)
       ↓
Sarvam STT (app/voice/stt.py - Saarika)
       ↓ (Transcript)
Language Detection (app/voice/language.py)
       ↓ (Intent & Constraints)
Conversation State (app/agent/state.py)
       ↓
Tools (app/agent/tools.py) & Agent (app/agent/agent.py - Sarvam 105b)
       ↓ (Response text)
Rime TTS (app/voice/rime.py)
       ↓ (Audio bytes)
Frontend Audio Playback & Voice Orb (SPEAKING → IDLE)
```

---

## Frontend

Built with:
- **Framework:** React 19 + TanStack Start (SSR) & TanStack Router
- **State Management:** TanStack Query + Custom Hooks (`useVoiceSession`, `useLanguageDetection`, `useTaskPipeline`)
- **Styling:** TailwindCSS v4 + shadcn/ui primitives + OKLCH color system
- **Microphone & Playback:** Browser `MediaRecorder` API + HTML5 Audio streaming
- **Icons & Typography:** Lucide React + Nunito Sans

Key frontend files:
- `frontend/src/config.ts`: Centralizes API (`http://localhost:8000`) and WebSocket (`ws://localhost:8000/ws/voice`) URLs.
- `frontend/src/services/voiceService.ts`: Manages browser microphone, WebSocket events, and Rime audio playback.
- `frontend/src/hooks/useVoiceSession.ts`: Exposes voice states, microphone toggle, permission handling, and transcripts.
- `frontend/src/components/sutra/dashboard.tsx`: Main voice session UI with Voice Orb, Language Panel, and Task Pipeline.

---

## Backend

Built with:
- **Framework:** FastAPI with CORS enabled for all origins
- **Server:** Uvicorn on port `8000`
- **Endpoints:**
  - `GET /health`: Health check endpoint
  - `GET /api/status`: Service status
  - `POST /api/chat`: Text chat endpoint
  - `WS /ws/voice`: Real-time bidirectional voice & state WebSocket

Key backend files:
- `app/main.py`: FastAPI application entry point with CORS and route mounting.
- `app/api/websocket.py`: WebSocket handler for audio streams, transcriptions, pipeline events, and state synchronization.
- `app/voice/stt.py`: Server-side Sarvam Speech-to-Text integration.
- `app/voice/language.py`: Multilingual and code-switching detection engine.
- `app/voice/rime.py`: Rime Text-to-Speech synthesis service.
- `app/agent/state.py`: Authoritative conversation state with versioning and constraint tracking.
- `app/agent/agent.py`: Sarvam LLM voice agent.
- `app/agent/tools.py`: Tool execution with stale result rejection.

---

## Voice Pipeline

1. **User speaks into microphone:** Browser captures audio using `MediaRecorder`.
2. **Audio dispatch:** Audio payload sent over WebSocket to `/ws/voice`.
3. **Speech-to-Text:** Backend receives audio bytes and transcribes via Sarvam AI Saarika model.
4. **Language detection:** Identifies primary language and code-switching (e.g. Hindi + English).
5. **State update:** Updates conversation state, intent, and constraints (e.g., date, origin, destination).
6. **Agent execution:** Agent generates assistant response considering full conversation history.
7. **Rime synthesis:** Rime TTS synthesizes spoken audio from assistant text.
8. **Audio playback:** Frontend receives audio bytes and plays response while Voice Orb animates in `SPEAKING` state.

---

## Multilingual / Code-Switching

SUTRA natively handles:
- **Single language:** Pure Hindi (`hi`), pure English (`en`), Bengali (`bn`), Sanskrit.
- **Code-switching:** Hinglish (mixed Hindi and English, e.g. *"Mujhe Kolkata se Delhi jaana hai, Saturday ko"*).
- **Auto-detection:** Sarvam STT model runs with `language_code: "unknown"`, allowing the model to detect and transcribe mixed speech automatically without manual language selection.

---

## Conversation State

Maintained authoritatively in `app/agent/state.py`:
- `session_id`: Unique conversation identifier.
- `messages`: Chronological message history across all turns.
- `intent`: Active intent (e.g., `flight_search`).
- `constraints`: Key-value constraints (e.g., `origin: "Kolkata"`, `destination: "Delhi"`, `date: "Saturday"`, `budget: "₹6,000"`).
- `language`: Detected language and code-switching flag.
- `active_task_id`: Current running task ID.
- `task_version`: Monotonically increasing version counter incremented whenever constraints change.

---

## Tool Execution

Tools represent asynchronous external operations (such as flight searches or database lookups):
- Implemented in `app/agent/tools.py`.
- `execute_tool(tool_name, arguments)` records the task version when the tool starts.
- Emits real-time pipeline events (`TOOL_STARTED`, `TOOL_COMPLETED`) over WebSocket to update the frontend Task Pipeline panel.

---

## Interruption and Cancellation

- **Interruption:** When the user speaks while the agent is speaking or working, the frontend dispatches an interruption signal to stop audio playback and notify the backend.
- **Cancellation:** The "Cancel task" button dispatches `{"type": "cancel"}` over WebSocket, executing `conversation_state.cancel_task()` and setting pipeline state to `CANCELLED`.

---

## Stale Result Protection

To prevent outdated results from corrupting the conversation:
- Each tool execution captures `task_id` and `task_version` at start.
- If the user provides a new constraint while a tool is running (e.g. changing date from "tomorrow" to "Saturday"), `task_version` increments.
- When the tool finishes, `is_task_current(task_id, task_version)` checks if the version has changed.
- Superseded results are flagged as `stale: True` and rejected (`stale_result_rejected`), ensuring only current results are communicated.

---

## Rime Voice Output

- Implemented in `app/voice/rime.py`.
- Uses Rime's `arcana` model with sampling rate `22050`.
- Voice can be configured via `RIME_VOICE` in `.env` (default: `"aria"`).
- Synthesized audio is base64-encoded and sent over WebSocket as `rime_audio` events for client playback.

---

## Project Structure

```
Sutra-VoiceAI/
├── app/
│   ├── agent/
│   │   ├── agent.py          # Voice agent (Sarvam LLM)
│   │   ├── state.py          # Conversation state & versioning
│   │   └── tools.py          # Tool execution & stale result protection
│   ├── api/
│   │   ├── routes.py         # REST endpoints (/health, /api/chat)
│   │   └── websocket.py      # Realtime voice WebSocket (/ws/voice)
│   ├── core/
│   │   ├── config.py         # Environment settings
│   │   └── logger.py         # Logger utility
│   ├── main.py               # FastAPI application entrypoint
│   └── voice/
│       ├── language.py       # Language detection service
│       ├── rime.py           # Rime TTS service
│       └── stt.py            # Sarvam STT service
├── frontend/
│   ├── src/
│   │   ├── components/       # SUTRA UI & shadcn/ui components
│   │   ├── config.ts         # Centralized frontend config
│   │   ├── hooks/            # Custom hooks (useVoiceSession, etc.)
│   │   ├── routes/           # TanStack Router routes
│   │   ├── services/         # API client & voice service
│   │   └── types/            # TypeScript data contracts
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   └── test_language.py      # Language detection tests
├── requirements.txt          # Python dependencies
└── README.md
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Sarvam AI Credentials (for LLM and STT)
SARVAM_API_KEY=your_sarvam_api_key
SARVAM_API_URL=https://api.sarvam.ai/v1/chat/completions
SARVAM_MODEL=sarvam-105b-conversations
SARVAM_STT_URL=https://api.sarvam.ai/speech-to-text

# Rime TTS Credentials
RIME_API_KEY=your_rime_api_key
RIME_VOICE=aria

# Application Settings
APP_ENV=development
DEBUG=true
```

In `frontend/.env` (optional, defaults to `http://localhost:8000`):
```env
VITE_API_URL=http://localhost:8000
```

---

## Running Locally

### 1. Start the Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
```

Backend will be available at:
- REST API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- WebSocket: `ws://localhost:8000/ws/voice`

### 2. Start the Frontend

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend will be available at:
- `http://localhost:8080`

---

## Testing

### Backend Unit Tests

```bash
python -m pytest tests
```

### Frontend Type Check & Build

```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## License

MIT
