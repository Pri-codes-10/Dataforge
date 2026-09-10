# Multilingual voice agent

A Python 3.11+ conversation-continuity foundation for the DataForge x Rime
challenge. The concrete scenario is a Hindi-English travel lookup whose budget
changes while a prior search is running. The live-provider layer is now implemented
using Gemini structured outputs, Deepgram STT and the official LiveKit Rime plugin.
Offline tests and a live Gemini/Rime provider smoke test pass. End-to-end audible
voice behavior still needs verification after the Rime HTTP streaming change.
Start with [LIVE_SETUP.md](LIVE_SETUP.md). This is not yet submission-ready.

## Run

From this directory, with Python 3.11 or newer (the replay needs no packages;
install requirements.txt to include provider adapter tests):

```powershell
python -m bench.run_tests
python -X utf8 -m app.demo
```

The replay prints structured JSON events. Tests write `bench/results/acceptance.csv`.
The fixture planner returns predefined actions; it does not interpret language.
Search results are synthetic and no bookings or external actions take place.

## Architecture and integration contract

`final raw STT transcript -> planner -> Action -> Orchestrator -> async tool -> playback`

The orchestrator owns per-session constraints, generation, active calls and history.
New constraints or intent advance generation and cancel work; status responses do
not. Tool output and planner completions are fenced. Constraint removal uses null.
Planning runs serially to preserve consecutive deltas. Tool execution stays async.
VAD must call `interrupt()` immediately on speech start, before STT/LLM latency.
Playback must stop already queued audio and reject old generations at consumption,
not merely at synthesis submission. All state mutations belong on one event loop.
The memory playback sink implements this contract only as a test simulation.
The live adapter interrupts LiveKit speech handles; device-level stop latency
still requires measurement. VAD holds new output while the user speaks. Status
during silent work preserves the running lookup; corrections invalidate output.
For new tasks the planner can explicitly reset constraints. Tools receive copied
constraints and return text, never arbitrary state patches.

Planner failure leaves state unchanged and logs an error; tool failures log their
type and submit a short failure response only if current. Logs intentionally omit
exception bodies but contain transcripts; use synthetic data for this milestone.
Tools must have bounded runtime and respect cancellation in production. A tool
that suppresses cancellation forever can hold shutdown open; generation fencing
still blocks its eventual result. A transport integration must supervise shutdown.

## Remaining verification

1. Configure provider keys and choose a compatible Rime model/voice/language.
2. Test Deepgram and the planner with recorded Hindi-English code-switching.
3. Measure physical playback interruption and cold/cached audible latency.
4. Capture the full voice demo and complete the evidence record.

## Rime integration record: implemented, not live-verified

No Rime audio has been synthesized by this milestone. Model ID, speaker and
language are required environment settings, not yet selected or tested.
The implemented endpoint is `https://users.rime.ai/v1/rime-tts`, with configurable base
URL. Region is provider-default and not locally verified. Requested audio is PCM
signed 16-bit mono at 24000 Hz. Transport is the official LiveKit Rime streaming HTTP
plugin with sentence segmentation, then console playback or WebRTC room output.
Rime is the only TTS path; no fallback is implemented. Startup JSONL records the
actual configuration. `.env.example` contains placeholders; keys stay server-side.

Documentation checked on 2026-09-09:
- https://docs.livekit.io/agents/models/tts/rime/ (currently marks Arcana retired)
- https://docs.rime.ai/docs/websockets (current WebSocket guidance)
- https://docs.livekit.io/agents/models/stt/deepgram/
- https://developers.openai.com/api/docs/guides/structured-outputs

Choose the model/voice/language from the live catalog before implementing the
voice path, then record the actual tested configuration here. Do not infer
code-switch quality from a language-support listing.
